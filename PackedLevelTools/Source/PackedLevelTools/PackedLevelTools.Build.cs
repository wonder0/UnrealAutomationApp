// using UnrealBuildTool;

// public class PackedLevelTools : ModuleRules
// {
//     public PackedLevelTools(ReadOnlyTargetRules Target) : base(Target)
//     {
//         PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

//         // IMPORTANT: This plugin uses Editor-only modules (UnrealEd, KismetCompiler).
//         // We must prevent UBT from trying to build this for a standalone Game/Client target.
//         if (Target.Type == TargetType.Editor)
//         {
//             PublicDependencyModuleNames.AddRange(
//                 new string[]
//                 {
//                     "Core",
//                     "CoreUObject",
//                     "Engine"
//                 }
//             );

//             PrivateDependencyModuleNames.AddRange(
//                 new string[]
//                 {
//                     "UnrealEd",
//                     "Slate",
//                     "SlateCore",
//                     "AssetRegistry",
//                     "Kismet",
//                     "KismetCompiler",
//                     "PythonScriptPlugin",
//                     "EditorFramework",
//                     "UnrealEd"
//                 }
//             );
//         }
//     }
// }

using UnrealBuildTool;

public class PackedLevelTools : ModuleRules
{
    public PackedLevelTools(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(
            new string[]
            {
                "Core",
                "CoreUObject",
                "Engine"
            }
        );

        // Only add Editor-only dependencies when building for the Editor
        if (Target.bBuildEditor)
        {
            PrivateDependencyModuleNames.AddRange(
                new string[]
                {
                    "UnrealEd",
                    "Slate",
                    "SlateCore",
                    "AssetRegistry",
                    "Kismet",
                    "KismetCompiler",
                    "PythonScriptPlugin"
                }
            );
        }
    }
}