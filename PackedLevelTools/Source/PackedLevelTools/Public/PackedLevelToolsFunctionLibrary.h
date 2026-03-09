#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "PackedLevelToolsFunctionLibrary.generated.h"

#if WITH_EDITOR
class APackedLevelActor;
#endif

UCLASS()
class PACKEDLEVELTOOLS_API UPackedLevelToolsFunctionLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:

#if WITH_EDITOR
    UFUNCTION(BlueprintCallable, CallInEditor, Category = "Packed Level")
    static APackedLevelActor* CreatePackedLevelActorFromCurrentLevel(const FString& TargetPackagePath);

    UFUNCTION(BlueprintCallable, CallInEditor, Category = "Packed Level")
    static APackedLevelActor* CreatePackedLevelActorFromWorldAsset(const FString& WorldAssetPath, const FString& TargetPackagePath);
#endif
};