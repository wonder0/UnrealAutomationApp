#include "PackedLevelToolsFunctionLibrary.h"

#if WITH_EDITOR
#include "Editor.h"
#include "Engine/World.h"
#include "Engine/Blueprint.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "PackedLevelActor/PackedLevelActor.h"
#include "PackedLevelActor/PackedLevelActorBuilder.h"
#include "FileHelpers.h"
#include "Misc/PackageName.h"
#include "UObject/SoftObjectPath.h"
#include "UObject/SavePackage.h"
#include "EngineUtils.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#endif

APackedLevelActor* UPackedLevelToolsFunctionLibrary::CreatePackedLevelActorFromCurrentLevel(const FString& TargetPackagePath)
{
#if WITH_EDITOR
    if (GEditor && GEditor->GetEditorWorldContext().World())
    {
        return CreatePackedLevelActorFromWorldAsset(
            GEditor->GetEditorWorldContext().World()->GetPathName(),
            TargetPackagePath
        );
    }
#endif
    return nullptr;
}

APackedLevelActor* UPackedLevelToolsFunctionLibrary::CreatePackedLevelActorFromWorldAsset(const FString& WorldAssetPath, const FString& TargetPackagePath)
{
#if WITH_EDITOR
    if (WorldAssetPath.IsEmpty() || TargetPackagePath.IsEmpty()) return nullptr;

    // ----------------------------------------------------------------
    // STEP 1: Load the source map into the editor
    // ----------------------------------------------------------------
    FString MapFilePath;
    if (!FPackageName::TryConvertLongPackageNameToFilename(WorldAssetPath, MapFilePath, FPackageName::GetMapPackageExtension()))
    {
        UE_LOG(LogTemp, Error, TEXT("Could not resolve map path: %s"), *WorldAssetPath);
        return nullptr;
    }

    bool bLoaded = FEditorFileUtils::LoadMap(MapFilePath, false, true);
    if (!bLoaded)
    {
        UE_LOG(LogTemp, Error, TEXT("LoadMap failed: %s"), *MapFilePath);
        return nullptr;
    }

    UWorld* LoadedWorld = GEditor->GetEditorWorldContext().World();
    if (!LoadedWorld)
    {
        UE_LOG(LogTemp, Error, TEXT("No active world after LoadMap."));
        return nullptr;
    }

    // ----------------------------------------------------------------
    // STEP 2: Collect all StaticMeshActors and group by mesh + material
    // ----------------------------------------------------------------
    // Key: StaticMesh pointer
    // Value: Array of world transforms
    TMap<UStaticMesh*, TArray<FTransform>> MeshTransformMap;

    // Also store materials per mesh (from first encountered actor)
    TMap<UStaticMesh*, TArray<UMaterialInterface*>> MeshMaterialMap;

    FVector PivotLocation = FVector::ZeroVector;
    int32 TotalActors = 0;

    for (TActorIterator<AStaticMeshActor> It(LoadedWorld); It; ++It)
    {
        AStaticMeshActor* SMActor = *It;
        if (!SMActor) continue;

        UStaticMeshComponent* SMComp = SMActor->GetStaticMeshComponent();
        if (!SMComp) continue;

        UStaticMesh* Mesh = SMComp->GetStaticMesh();
        if (!Mesh) continue;

        FTransform WorldTransform = SMActor->GetActorTransform();
        MeshTransformMap.FindOrAdd(Mesh).Add(WorldTransform);

        // Store materials from first actor with this mesh
        if (!MeshMaterialMap.Contains(Mesh))
        {
            TArray<UMaterialInterface*> Mats;
            for (int32 m = 0; m < SMComp->GetNumMaterials(); ++m)
            {
                Mats.Add(SMComp->GetMaterial(m));
            }
            MeshMaterialMap.Add(Mesh, Mats);
        }

        PivotLocation += WorldTransform.GetLocation();
        TotalActors++;
    }

    if (TotalActors == 0)
    {
        UE_LOG(LogTemp, Error, TEXT("No StaticMeshActors found in: %s"), *WorldAssetPath);
        return nullptr;
    }

    // Compute centroid as pivot
    PivotLocation /= (float)TotalActors;

    UE_LOG(LogTemp, Log, TEXT("Found %d actors, %d unique meshes. Pivot: %s"),
        TotalActors, MeshTransformMap.Num(), *PivotLocation.ToString());

    // ----------------------------------------------------------------
    // STEP 3: Create the Blueprint asset
    // ----------------------------------------------------------------
    FString AssetName = FPackageName::GetLongPackageAssetName(TargetPackagePath);

    // Create the package
    UPackage* BPPackage = CreatePackage(*TargetPackagePath);
    if (!BPPackage)
    {
        UE_LOG(LogTemp, Error, TEXT("Failed to create package: %s"), *TargetPackagePath);
        return nullptr;
    }
    BPPackage->FullyLoad();

    // Create a Blueprint with APackedLevelActor as parent
    UBlueprint* NewBP = FKismetEditorUtilities::CreateBlueprint(
        APackedLevelActor::StaticClass(),
        BPPackage,
        *AssetName,
        BPTYPE_Normal,
        UBlueprint::StaticClass(),
        UBlueprintGeneratedClass::StaticClass()
    );

    if (!NewBP)
    {
        UE_LOG(LogTemp, Error, TEXT("Failed to create Blueprint: %s"), *AssetName);
        return nullptr;
    }

    // ----------------------------------------------------------------
    // STEP 4: Add one ISM component per unique mesh via SCS
    // ----------------------------------------------------------------
    USimpleConstructionScript* SCS = NewBP->SimpleConstructionScript;
    if (!SCS)
    {
        UE_LOG(LogTemp, Error, TEXT("Blueprint has no SimpleConstructionScript."));
        return nullptr;
    }

    const FName PackedTag = APackedLevelActor::GetPackedComponentTag();

    for (auto& Pair : MeshTransformMap)
    {
        UStaticMesh* Mesh = Pair.Key;
        TArray<FTransform>& Transforms = Pair.Value;

        if (!Mesh || Transforms.Num() == 0) continue;

        // Create SCS node for ISM
        USCS_Node* ISMNode = SCS->CreateNode(UInstancedStaticMeshComponent::StaticClass());
        if (!ISMNode) continue;

        UInstancedStaticMeshComponent* ISMComp =
            Cast<UInstancedStaticMeshComponent>(ISMNode->ComponentTemplate);
        if (!ISMComp) continue;

        // Set mesh
        ISMComp->SetStaticMesh(Mesh);

        // Set materials
        if (TArray<UMaterialInterface*>* Mats = MeshMaterialMap.Find(Mesh))
        {
            for (int32 m = 0; m < Mats->Num(); ++m)
            {
                if ((*Mats)[m])
                {
                    ISMComp->SetMaterial(m, (*Mats)[m]);
                }
            }
        }

        // Add instances (relative to pivot)
        for (const FTransform& WorldT : Transforms)
        {
            FTransform RelativeT = WorldT;
            RelativeT.SetLocation(WorldT.GetLocation() - PivotLocation);
            ISMComp->AddInstance(RelativeT, false);
        }

        // Tag as packed component
        ISMComp->ComponentTags.Add(PackedTag);

        // Attach to root
        SCS->AddNode(ISMNode);
        USCS_Node* RootNode = SCS->GetDefaultSceneRootNode();
        if (RootNode)
        {
            RootNode->AddChildNode(ISMNode);
        }

        UE_LOG(LogTemp, Log, TEXT("  ISM: %s | %d instances"), *Mesh->GetName(), Transforms.Num());
    }

    // ----------------------------------------------------------------
    // STEP 5: Compile and Save
    // ----------------------------------------------------------------
    FKismetEditorUtilities::CompileBlueprint(NewBP);
    NewBP->MarkPackageDirty();

    // Save the package to disk
    FSavePackageArgs SaveArgs;
    SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
    SaveArgs.Error = GError;
    SaveArgs.bForceByteSwapping = false;
    SaveArgs.bWarnOfLongFilename = true;

    FString SavePath;
    FPackageName::TryConvertLongPackageNameToFilename(
        TargetPackagePath, SavePath, FPackageName::GetAssetPackageExtension()
    );

    UPackage::Save(BPPackage, NewBP, *SavePath, SaveArgs);

    UE_LOG(LogTemp, Log, TEXT("Saved Blueprint: %s"), *SavePath);

    // Notify asset registry
    FAssetRegistryModule::AssetCreated(NewBP);

    // Return CDO
    if (NewBP->GeneratedClass)
    {
        return Cast<APackedLevelActor>(NewBP->GeneratedClass->GetDefaultObject());
    }

#endif
    return nullptr;
}