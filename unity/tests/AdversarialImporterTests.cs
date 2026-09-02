// ====================================================================================================================
// AdversarialImporterTests.cs - Adversarial & Boundary Stress Test Suite for Unity Importer
// ====================================================================================================================

using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using WorldGen.Core;
using WorldGen.Editor;

namespace WorldGen.Tests
{
    public class AdversarialImporterTestRunner
    {
        private static int passedTests = 0;
        private static int failedTests = 0;
        private static List<string> failureDetails = new List<string>();

        public static int Main(string[] args)
        {
            Console.WriteLine("================================================================");
            Console.WriteLine("     ADVERSARIAL STRESS TEST SUITE: UNITY IMPORTER (R4)         ");
            Console.WriteLine("================================================================");

            // Group 1: JSON Parser Adversarial Fuzzing & Malformed Inputs
            RunTest("ADV_01_MalformedJson_UnclosedBraces", Test_MalformedJson_UnclosedBraces);
            RunTest("ADV_02_MalformedJson_TrailingCommasAndTokens", Test_MalformedJson_TrailingCommasAndTokens);
            RunTest("ADV_03_MalformedJson_NullAndEmptyObjects", Test_MalformedJson_NullAndEmptyObjects);
            RunTest("ADV_04_MalformedJson_ExtremeNumbersAndScientificNotation", Test_MalformedJson_ExtremeNumbersAndScientificNotation);
            RunTest("ADV_05_MalformedJson_NullCollectionsAndMissingKeys", Test_MalformedJson_NullCollectionsAndMissingKeys);
            RunTest("ADV_06_MalformedJson_UnicodeAndEscapes", Test_MalformedJson_UnicodeAndEscapes);

            // Group 2: Heightmap & Terrain Math Adversarial Cases
            RunTest("ADV_07_Terrain_NonSquare2DHeightmapResampling", Test_Terrain_NonSquare2DHeightmapResampling);
            RunTest("ADV_08_Terrain_1DHeightmapNonSquareLength", Test_Terrain_1DHeightmapNonSquareLength);
            RunTest("ADV_09_Terrain_NegativeAndZeroDimensions", Test_Terrain_NegativeAndZeroDimensions);
            RunTest("ADV_10_Terrain_ExtremeAndNegativeHeightsNormalization", Test_Terrain_ExtremeAndNegativeHeightsNormalization);
            RunTest("ADV_11_Terrain_FlatAndSpikeHeightmaps", Test_Terrain_FlatAndSpikeHeightmaps);
            RunTest("ADV_12_Terrain_ResolutionBoundaryCalculation", Test_Terrain_ResolutionBoundaryCalculation);

            // Group 3: Prefabs & Bounding Box Adversarial Cases
            RunTest("ADV_13_Prefab_UnknownAndMissingPrefabSpawnsProxy", Test_Prefab_UnknownAndMissingPrefabSpawnsProxy);
            RunTest("ADV_14_Prefab_MissingBboxAndInvertedMinMax", Test_Prefab_MissingBboxAndInvertedMinMax);
            RunTest("ADV_15_Prefab_ZeroScaleAndDegenerateQuaternions", Test_Prefab_ZeroScaleAndDegenerateQuaternions);
            RunTest("ADV_16_Prefab_UnmatchedZoneIdsAndOrphanedBuildings", Test_Prefab_UnmatchedZoneIdsAndOrphanedBuildings);

            // Group 4: Faction & Destruction Material Swapper Adversarial Cases
            RunTest("ADV_17_Material_NonStandardFactionStrings", Test_Material_NonStandardFactionStrings);
            RunTest("ADV_18_Material_NonStandardDestructionStrings", Test_Material_NonStandardDestructionStrings);
            RunTest("ADV_19_Material_ProtectedMaterialsExclusion", Test_Material_ProtectedMaterialsExclusion);
            RunTest("ADV_20_Material_SwappableKeywordsCoverage", Test_Material_SwappableKeywordsCoverage);
            RunTest("ADV_21_Material_MissingMaterialFallbackTextureSwap", Test_Material_MissingMaterialFallbackTextureSwap);

            // Group 5: Road Ribbon & Spline Adversarial Cases
            RunTest("ADV_22_Road_SingleWaypointAndEmptyRoad", Test_Road_SingleWaypointAndEmptyRoad);
            RunTest("ADV_23_Road_DuplicateConsecutiveWaypointsFiltering", Test_Road_DuplicateConsecutiveWaypointsFiltering);
            RunTest("ADV_24_Road_VerticalWaypointsGimbalLockAvoidance", Test_Road_VerticalWaypointsGimbalLockAvoidance);
            RunTest("ADV_25_Road_NegativeAndExtremeRoadWidth", Test_Road_NegativeAndExtremeRoadWidth);
            RunTest("ADV_26_Road_CatmullRomLoopAndColinearPoints", Test_Road_CatmullRomLoopAndColinearPoints);

            // Group 6: Extreme Stress & Scale Fuzzing
            RunTest("ADV_27_Scale_LargeBuildingCountBatching", Test_Scale_LargeBuildingCountBatching);
            RunTest("ADV_28_TypeCoercion_StringIntegersAndFloatResolutions", Test_TypeCoercion_StringIntegersAndFloatResolutions);
            RunTest("ADV_29_Terrain_InvertedMinMaxElevationManifest", Test_Terrain_InvertedMinMaxElevationManifest);
            RunTest("ADV_30_Road_AcuteZigzagAndSharpHairpins", Test_Road_AcuteZigzagAndSharpHairpins);

            // Group 7: Adaptive Decimated Mesh & V2 Templated Hierarchy Adversarial Cases
            RunTest("ADV_31_AdaptiveMesh_EmptyOrDegenerateMeshData", Test_AdaptiveMesh_EmptyOrDegenerateMeshData);
            RunTest("ADV_32_AdaptiveMesh_FlatArrayLengthNotMultipleOfThree", Test_AdaptiveMesh_FlatArrayLengthNotMultipleOfThree);
            RunTest("ADV_33_AdaptiveMesh_MissingNormalsAndUVsFallback", Test_AdaptiveMesh_MissingNormalsAndUVsFallback);
            RunTest("ADV_34_TemplatedZone_NullDistrictAndOrphanedPlacementRole", Test_TemplatedZone_NullDistrictAndOrphanedPlacementRole);
            RunTest("ADV_35_AdaptiveMesh_32BitLargeMeshStress", Test_AdaptiveMesh_32BitLargeMeshStress);
            RunTest("ADV_36_AdaptiveMesh_MalformedJsonWithMixedNullAttributes", Test_AdaptiveMesh_MalformedJsonWithMixedNullAttributes);

            Console.WriteLine("================================================================");
            Console.WriteLine($"TOTAL ADVERSARIAL TESTS: {passedTests + failedTests}");
            Console.WriteLine($"PASSED: {passedTests}");
            Console.WriteLine($"FAILED: {failedTests}");
            Console.WriteLine("================================================================");

            if (failureDetails.Count > 0)
            {
                Console.WriteLine("FAILURE BREAKDOWN:");
                foreach (var detail in failureDetails)
                {
                    Console.WriteLine($" - {detail}");
                }
            }

            return failedTests == 0 ? 0 : 1;
        }

        private static void RunTest(string testName, Action testAction)
        {
            try
            {
                testAction();
                Console.WriteLine($"[PASS] {testName}");
                passedTests++;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[FAIL] {testName} - {ex.Message}");
                failureDetails.Add($"{testName}: {ex.Message}");
                failedTests++;
            }
        }

        private static void Assert(bool condition, string message)
        {
            if (!condition)
                throw new Exception($"Assertion Failed: {message}");
        }

        private static void AssertEqual<T>(T expected, T actual, string message)
        {
            if (!EqualityComparer<T>.Default.Equals(expected, actual))
                throw new Exception($"Assertion Failed: {message}. Expected: '{expected}', Actual: '{actual}'");
        }

        private static void AssertApproxEqual(float expected, float actual, float tolerance, string message)
        {
            if (Math.Abs(expected - actual) > tolerance)
                throw new Exception($"Assertion Failed: {message}. Expected: {expected} (+/-{tolerance}), Actual: {actual}");
        }

        #region Group 1: JSON Parser Adversarial Fuzzing

        private static void Test_MalformedJson_UnclosedBraces()
        {
            string[] malformedCases = new string[]
            {
                "{ \"metadata\": { \"seed\": 42",
                "{ \"terrain\": { \"resolution\": 129 }",
                "[ { \"id\": \"zone_0\" ",
                "{ \"zones\": [ { \"id\": \"zone_0\" } ",
            };

            foreach (var json in malformedCases)
            {
                bool threw = false;
                try
                {
                    ManifestJsonParser.Parse(json);
                }
                catch (FormatException)
                {
                    threw = true;
                }
                catch (Exception ex)
                {
                    threw = true;
                }
                Assert(threw, $"Unclosed JSON should throw exception: {json}");
            }
        }

        private static void Test_MalformedJson_TrailingCommasAndTokens()
        {
            // Parser handles objects with unexpected tokens by throwing FormatException cleanly
            string invalidTokenJson = "{ \"metadata\": { \"seed\": @#$! } }";
            bool threw = false;
            try
            {
                ManifestJsonParser.Parse(invalidTokenJson);
            }
            catch (Exception)
            {
                threw = true;
            }
            Assert(threw, "Invalid tokens must throw FormatException");
        }

        private static void Test_MalformedJson_NullAndEmptyObjects()
        {
            // Empty valid JSON object
            string emptyObj = "{}";
            WorldManifest m1 = ManifestJsonParser.Parse(emptyObj);
            Assert(m1 != null, "Empty object should produce initialized WorldManifest instance");
            Assert(m1.metadata != null, "Metadata initialized");
            Assert(m1.terrain != null, "Terrain initialized");
            Assert(m1.zones != null && m1.zones.Count == 0, "Zones initialized empty");
            Assert(m1.buildings != null && m1.buildings.Count == 0, "Buildings initialized empty");
            Assert(m1.roads != null && m1.roads.Count == 0, "Roads initialized empty");

            // Manifest with null fields
            string nullFieldsJson = @"{
                ""metadata"": null,
                ""terrain"": null,
                ""zones"": null,
                ""buildings"": null,
                ""roads"": null
            }";
            WorldManifest m2 = ManifestJsonParser.Parse(nullFieldsJson);
            Assert(m2 != null, "Null fields JSON should parse safely without crashing");
        }

        private static void Test_MalformedJson_ExtremeNumbersAndScientificNotation()
        {
            string extremeJson = @"{
                ""metadata"": {
                    ""seed"": 999999999,
                    ""bounds"": [-1e5, -500.25, 0.0, 1e5, 500.75, 1.2e4]
                },
                ""terrain"": {
                    ""resolution"": 513,
                    ""world_size"": [10000.0, 1500.0, 10000.0],
                    ""min_height"": -999.99,
                    ""max_height"": 1e4,
                    ""heightmap"": [
                        [1e-4, 5.5e1, 100.0],
                        [-10.5, 0.0, 999.99]
                    ]
                }
            }";

            WorldManifest manifest = ManifestJsonParser.Parse(extremeJson);
            AssertEqual(999999999, manifest.metadata.seed, "Seed matches large int");
            AssertApproxEqual(10000.0f, manifest.terrain.GetWidth(), 0.1f, "Width parses 10000.0");
            Assert(manifest.terrain.raw_heightmap_2d != null, "2D heightmap parsed with scientific notation");
            AssertApproxEqual(55.0f, manifest.terrain.raw_heightmap_2d[0, 1], 0.1f, "5.5e1 -> 55.0");
        }

        private static void Test_MalformedJson_NullCollectionsAndMissingKeys()
        {
            string partialJson = @"{
                ""zones"": [
                    { ""id"": ""z0"" },
                    null,
                    { ""id"": ""z1"", ""faction"": null, ""center"": null, ""footprint_points"": null }
                ],
                ""buildings"": [
                    { ""id"": ""b0"", ""position"": null, ""rotation"": null, ""scale"": null, ""bounding_box"": null }
                ],
                ""roads"": [
                    { ""id"": ""r0"", ""waypoints"": null }
                ]
            }";

            WorldManifest manifest = ManifestJsonParser.Parse(partialJson);
            Assert(manifest != null, "Parsed partial JSON with null items");
            AssertEqual(2, manifest.zones.Count, "2 valid zones extracted, null item skipped");
            AssertEqual("A", manifest.zones[1].GetNormalizedFaction(), "Null faction defaults to 'A'");
            AssertEqual(Vector3.zero, manifest.zones[1].GetCenterVector(), "Null center defaults to Vector3.zero");
            AssertEqual(1, manifest.buildings.Count, "Building parsed");
            AssertEqual(Vector3.zero, manifest.buildings[0].GetPosition(), "Null position defaults to Vector3.zero");
            AssertEqual(Quaternion.identity, manifest.buildings[0].GetRotation(), "Null rotation defaults to Quaternion.identity");
            AssertEqual(Vector3.one, manifest.buildings[0].GetScale(), "Null scale defaults to Vector3.one");
        }

        private static void Test_MalformedJson_UnicodeAndEscapes()
        {
            string unicodeJson = @"{
                ""metadata"": {
                    ""generator"": ""Procedural \u0057orldGen \u2694\ufe0f \n\t\\ Special Edition""
                },
                ""zones"": [
                    { ""id"": ""zone_\u0041"", ""name"": ""Bunker \u03a9"" }
                ]
            }";

            WorldManifest manifest = ManifestJsonParser.Parse(unicodeJson);
            Assert(manifest.metadata.generator.Contains("WorldGen"), "Unicode \\u0057 escaped to 'W'");
            AssertEqual("zone_A", manifest.zones[0].id, "Unicode \\u0041 escaped to 'A'");
            AssertEqual("Bunker \u03a9", manifest.zones[0].name, "Unicode greek omega preserved");
        }

        #endregion

        #region Group 2: Heightmap & Terrain Math

        private static void Test_Terrain_NonSquare2DHeightmapResampling()
        {
            // Non-square heightmap: 4 rows (Z) x 8 cols (X)
            float[,] nonSquare = new float[4, 8];
            for (int r = 0; r < 4; r++)
                for (int c = 0; c < 8; c++)
                    nonSquare[r, c] = (r * 10f) + (c * 5f);

            var manifest = new TerrainManifest
            {
                resolution = 65,
                width = 500f,
                length = 250f,
                height_scale = 100f,
                raw_heightmap_2d = nonSquare
            };

            float[,] resampled = TerrainGenerator.ResampleHeightmap(manifest, 65, 100f);
            AssertEqual(65, resampled.GetLength(0), "Target rows");
            AssertEqual(65, resampled.GetLength(1), "Target cols");

            // All values must be valid non-NaN normalized floats
            for (int z = 0; z < 65; z++)
            {
                for (int x = 0; x < 65; x++)
                {
                    float val = resampled[z, x];
                    Assert(!float.IsNaN(val), $"Resampled height at [{z},{x}] is NaN");
                    Assert(!float.IsInfinity(val), $"Resampled height at [{z},{x}] is Infinity");
                    Assert(val >= 0.0f && val <= 1.0f, $"Resampled height [{z},{x}]={val} out of bounds");
                }
            }
        }

        private static void Test_Terrain_1DHeightmapNonSquareLength()
        {
            // 1D heightmap with length 10 (not a perfect square)
            float[] data = new float[] { 0, 10, 20, 30, 40, 50, 60, 70, 80, 90 };
            var manifest = new TerrainManifest
            {
                height_scale = 100f,
                raw_heightmap_1d = data
            };

            float[,] resampled = TerrainGenerator.ResampleHeightmap(manifest, 65, 100f);
            Assert(resampled != null, "Resampling 1D non-square heightmap succeeds");
            for (int z = 0; z < 65; z++)
            {
                for (int x = 0; x < 65; x++)
                {
                    float val = resampled[z, x];
                    Assert(!float.IsNaN(val), "No NaN in non-square 1D resample");
                }
            }
        }

        private static void Test_Terrain_NegativeAndZeroDimensions()
        {
            var manifest = new TerrainManifest
            {
                world_size = new float[] { -1000f, 0f, -500f },
                width = -1000f,
                height_scale = 0f,
                length = -500f
            };

            // GetWidth/GetHeightScale/GetLength should fallback gracefully to positive defaults
            Assert(manifest.GetWidth() > 0, "Negative width falls back to default > 0");
            Assert(manifest.GetHeightScale() > 0, "Zero height_scale falls back to default > 0");
            Assert(manifest.GetLength() > 0, "Negative length falls back to default > 0");
        }

        private static void Test_Terrain_ExtremeAndNegativeHeightsNormalization()
        {
            var manifest = new TerrainManifest
            {
                height_scale = 150f,
                raw_heightmap_2d = new float[,]
                {
                    { -1000f, -50f },
                    { 300f, 5000f }
                }
            };

            float[,] resampled = TerrainGenerator.ResampleHeightmap(manifest, 65, 150f);
            AssertApproxEqual(0.0f, resampled[0, 0], 0.001f, "Negative height clamped to 0.0");
            AssertApproxEqual(1.0f, resampled[64, 64], 0.001f, "Excessive height clamped to 1.0");
        }

        private static void Test_Terrain_FlatAndSpikeHeightmaps()
        {
            // 1. All-zero flat heightmap
            var flat = new TerrainManifest
            {
                height_scale = 150f,
                raw_heightmap_2d = new float[,] { { 0f, 0f }, { 0f, 0f } }
            };
            float[,] resampledFlat = TerrainGenerator.ResampleHeightmap(flat, 65, 150f);
            AssertApproxEqual(0.0f, resampledFlat[32, 32], 0.001f, "Flat heightmap yields 0.0");

            // 2. Single spike heightmap
            var spike = new TerrainManifest
            {
                height_scale = 100f,
                raw_heightmap_2d = new float[,] { { 0f, 0f }, { 0f, 100f } }
            };
            float[,] resampledSpike = TerrainGenerator.ResampleHeightmap(spike, 65, 100f);
            AssertApproxEqual(1.0f, resampledSpike[64, 64], 0.001f, "Spike corner is 1.0");
            AssertApproxEqual(0.25f, resampledSpike[32, 32], 0.05f, "Bilinear middle is 0.25");
        }

        private static void Test_Terrain_ResolutionBoundaryCalculation()
        {
            AssertEqual(65, TerrainGenerator.CalculateUnityHeightmapResolution(0), "Res 0 -> 65");
            AssertEqual(65, TerrainGenerator.CalculateUnityHeightmapResolution(-100), "Res -100 -> 65");
            AssertEqual(65, TerrainGenerator.CalculateUnityHeightmapResolution(65), "Res 65 -> 65");
            AssertEqual(129, TerrainGenerator.CalculateUnityHeightmapResolution(66), "Res 66 -> 129");
            AssertEqual(4097, TerrainGenerator.CalculateUnityHeightmapResolution(5000), "Res 5000 -> 4097");
        }

        #endregion

        #region Group 3: Prefabs & Bounding Box

        private static void Test_Prefab_UnknownAndMissingPrefabSpawnsProxy()
        {
            var bld = new BuildingManifest
            {
                prefab_name = "SM_Unknown_SuperStructure_X99",
                bounding_box = new BoundingBoxManifest
                {
                    size = new float[] { 12f, 6f, 14f }
                }
            };

            var go = PrefabSpawner.SpawnBuilding(bld, null, null, "NonExistentDirectory");
            Assert(go != null, "Fallback proxy spawned for non-existent prefab");
            Assert(go.name.Contains("Proxy") || go.name.Contains("SM_Unknown"), "Proxy name set");
            AssertApproxEqual(12f, go.transform.localScale.x, 0.01f, "Proxy scaled to bbox size X");
            AssertApproxEqual(6f, go.transform.localScale.y, 0.01f, "Proxy scaled to bbox size Y");
            AssertApproxEqual(14f, go.transform.localScale.z, 0.01f, "Proxy scaled to bbox size Z");
        }

        private static void Test_Prefab_MissingBboxAndInvertedMinMax()
        {
            // 1. Missing bbox
            var bldNoBbox = new BuildingManifest { prefab_name = "SM_Bld_Empty" };
            BoundingBoxManifest bbox = bldNoBbox.GetBoundingBox();
            Assert(bbox != null, "Default bounding box returned when null");
            AssertEqual(Vector3.one, bbox.GetSize(), "Default bbox size is Vector3.one");

            // 2. Inverted min/max: min > max
            var invertedBbox = new BoundingBoxManifest
            {
                min = new float[] { 10f, 20f, 30f },
                max = new float[] { 5f, 10f, 15f },
                size = null
            };
            Vector3 size = invertedBbox.GetSize();
            AssertApproxEqual(5f, size.x, 0.01f, "Inverted X min/max handles Abs");
            AssertApproxEqual(10f, size.y, 0.01f, "Inverted Y min/max handles Abs");
            AssertApproxEqual(15f, size.z, 0.01f, "Inverted Z min/max handles Abs");
        }

        private static void Test_Prefab_ZeroScaleAndDegenerateQuaternions()
        {
            // Degenerate zero quaternion [0, 0, 0, 0]
            var bld = new BuildingManifest
            {
                rotation = new float[] { 0f, 0f, 0f, 0f }
            };
            Quaternion rot = bld.GetRotation();
            AssertEqual(Quaternion.identity, rot, "Zero quaternion falls back to Quaternion.identity");

            // Euler rotation with 3 elements
            var bldEuler = new BuildingManifest
            {
                rotation = new float[] { 0f, 45f, 0f }
            };
            Quaternion rotEuler = bldEuler.GetRotation();
            Assert(rotEuler.w != 0f || rotEuler.x != 0f || rotEuler.y != 0f || rotEuler.z != 0f, "Euler rotation converted");
        }

        private static void Test_Prefab_UnmatchedZoneIdsAndOrphanedBuildings()
        {
            var bld = new BuildingManifest
            {
                id = "bld_orphan",
                zone_id = "non_existent_zone_99",
                prefab_name = "SM_Bld_Tent_01"
            };

            var parent = new GameObject("Root");
            var spawned = PrefabSpawner.SpawnBuilding(bld, null, parent.transform, "Assets/PolygonMilitary/Prefabs");
            Assert(spawned != null, "Orphaned building spawns under fallback parent");
            AssertEqual(parent.transform, spawned.transform.parent, "Spawned under root parent");
        }

        #endregion

        #region Group 4: Faction & Destruction Material Swapper

        private static void Test_Material_NonStandardFactionStrings()
        {
            AssertEqual("A", MaterialSwapper.NormalizeFaction(null), "Null faction -> 'A'");
            AssertEqual("A", MaterialSwapper.NormalizeFaction(""), "Empty faction -> 'A'");
            AssertEqual("A", MaterialSwapper.NormalizeFaction("  "), "Whitespace faction -> 'A'");
            AssertEqual("A", MaterialSwapper.NormalizeFaction("a"), "Lowercase 'a' -> 'A'");
            AssertEqual("B", MaterialSwapper.NormalizeFaction("Faction_B"), "Suffix 'B' -> 'B'");
            AssertEqual("C", MaterialSwapper.NormalizeFaction("team_c"), "Suffix 'c' -> 'C'");
            AssertEqual("A", MaterialSwapper.NormalizeFaction("unknown_xyz"), "Unknown -> 'A'");
        }

        private static void Test_Material_NonStandardDestructionStrings()
        {
            AssertEqual("01", MaterialSwapper.NormalizeDestruction(null), "Null destruction -> '01'");
            AssertEqual("01", MaterialSwapper.NormalizeDestruction(""), "Empty destruction -> '01'");
            AssertEqual("01", MaterialSwapper.NormalizeDestruction("1"), "Single digit '1' -> '01'");
            AssertEqual("02", MaterialSwapper.NormalizeDestruction("2"), "Single digit '2' -> '02'");
            AssertEqual("03", MaterialSwapper.NormalizeDestruction("3"), "Single digit '3' -> '03'");
            AssertEqual("04", MaterialSwapper.NormalizeDestruction("4"), "Single digit '4' -> '04'");
            AssertEqual("01", MaterialSwapper.NormalizeDestruction("pristine"), "Unknown word -> '01'");
            AssertEqual("01", MaterialSwapper.NormalizeDestruction("99"), "Out of range '99' -> '01'");
        }

        private static void Test_Material_ProtectedMaterialsExclusion()
        {
            string[] protectedList = new string[]
            {
                "PolygonMilitary_Glass_01",
                "Glass_Transparent_Mat",
                "PolygonMilitary_Vehicles_01",
                "Vehicles_Texture_Mat",
                "Decal_Bullet_Hole_Mat",
                "FX_Fire_Particle_Mat",
                "Water_Ocean_Mat",
                "Screen_Computer_Mat",
                "UI_Icon_Mat"
            };

            foreach (var mat in protectedList)
            {
                Assert(MaterialSwapper.IsProtectedMaterial(mat), $"Protected material '{mat}' must be recognized");
            }
        }

        private static void Test_Material_SwappableKeywordsCoverage()
        {
            string[] swappableList = new string[]
            {
                "PolygonMilitary_Mat_01_A",
                "PolygonMilitary_Mat_02_B",
                "PolygonMilitary_Mat_03_C",
                "PolygonMilitary_Mat_04_A",
                "Military_Mat_Standard",
                "Mat_01_A_Building",
                "Standard_Material"
            };

            foreach (var mat in swappableList)
            {
                Assert(MaterialSwapper.IsSwappableMaterial(mat), $"Swappable material '{mat}' must be recognized");
            }
        }

        private static void Test_Material_MissingMaterialFallbackTextureSwap()
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            var rend = go.GetComponent<MeshRenderer>();
            rend.sharedMaterials = new Material[] { new Material(Shader.Find("Standard")) { name = "PolygonMilitary_Mat_01_A" } };

            MaterialSwapper.ApplyZoneTheme(go, "FactionB", "03", "NonExistentMaterialsFolder", "NonExistentTexturesFolder");
            // Should not crash even when search folders don't exist
            Assert(rend.sharedMaterials.Length == 1, "Shared material retained");
        }

        #endregion

        #region Group 5: Road Ribbon & Spline

        private static void Test_Road_SingleWaypointAndEmptyRoad()
        {
            var roadEmpty = new RoadManifest { id = "r_empty", waypoints = new List<float[]>() };
            var go1 = RoadMeshBuilder.BuildRoad(roadEmpty, null, null);
            Assert(go1 == null, "Empty waypoints road returns null");

            var roadSingle = new RoadManifest
            {
                id = "r_single",
                waypoints = new List<float[]> { new float[] { 10f, 0f, 10f } }
            };
            var go2 = RoadMeshBuilder.BuildRoad(roadSingle, null, null);
            Assert(go2 == null, "Single waypoint road returns null");
        }

        private static void Test_Road_DuplicateConsecutiveWaypointsFiltering()
        {
            var road = new RoadManifest
            {
                id = "r_dups",
                waypoints = new List<float[]>
                {
                    new float[] { 0f, 0f, 0f },
                    new float[] { 0f, 0f, 0f }, // Duplicate
                    new float[] { 0.01f, 0f, 0.01f }, // Near-duplicate (<0.1m)
                    new float[] { 50f, 5f, 50f },
                    new float[] { 100f, 10f, 100f }
                }
            };

            var roadGO = RoadMeshBuilder.BuildRoad(road, null, null, true, true);
            Assert(roadGO != null, "Road built successfully with duplicates filtered");
            MeshFilter mf = roadGO.GetComponent<MeshFilter>();
            Assert(mf != null && mf.sharedMesh != null, "MeshFilter generated without NaN");
            foreach (var v in mf.sharedMesh.vertices)
            {
                Assert(!float.IsNaN(v.x) && !float.IsNaN(v.y) && !float.IsNaN(v.z), "Vertices have no NaN values");
            }
        }

        private static void Test_Road_VerticalWaypointsGimbalLockAvoidance()
        {
            // Vertical road straight up along Y (tangent = Vector3.up)
            var road = new RoadManifest
            {
                id = "r_vert",
                waypoints = new List<float[]>
                {
                    new float[] { 50f, 0f, 50f },
                    new float[] { 50f, 50f, 50f },
                    new float[] { 50f, 100f, 50f }
                }
            };

            var roadGO = RoadMeshBuilder.BuildRoad(road, null, null, true, false);
            Assert(roadGO != null, "Vertical road generated without crashing cross-product singularity");
            MeshFilter mf = roadGO.GetComponent<MeshFilter>();
            Assert(mf.sharedMesh.vertices.Length > 0, "Ribbon vertices generated");
            foreach (var v in mf.sharedMesh.vertices)
            {
                Assert(!float.IsNaN(v.x), "Vertical road vertex X is valid");
                Assert(!float.IsNaN(v.y), "Vertical road vertex Y is valid");
                Assert(!float.IsNaN(v.z), "Vertical road vertex Z is valid");
            }
        }

        private static void Test_Road_NegativeAndExtremeRoadWidth()
        {
            // Negative width should fallback to default 6.0m
            var roadNeg = new RoadManifest
            {
                id = "r_neg_width",
                width = -10f,
                waypoints = new List<float[]>
                {
                    new float[] { 0f, 0f, 0f },
                    new float[] { 50f, 0f, 50f }
                }
            };
            var go1 = RoadMeshBuilder.BuildRoad(roadNeg, null, null);
            Assert(go1 != null, "Negative width road spawned");

            // Extreme road width 500m
            var roadWide = new RoadManifest
            {
                id = "r_wide",
                width = 500f,
                waypoints = new List<float[]>
                {
                    new float[] { 0f, 0f, 0f },
                    new float[] { 50f, 0f, 50f }
                }
            };
            var go2 = RoadMeshBuilder.BuildRoad(roadWide, null, null);
            Assert(go2 != null, "Wide road spawned");
        }

        private static void Test_Road_CatmullRomLoopAndColinearPoints()
        {
            var loopWaypoints = new List<Vector3>
            {
                new Vector3(0, 0, 0),
                new Vector3(100, 0, 0),
                new Vector3(100, 0, 100),
                new Vector3(0, 0, 100),
                new Vector3(0, 0, 0)
            };

            List<Vector3> spline = RoadMeshBuilder.SampleCatmullRomSpline(loopWaypoints, 8);
            Assert(spline.Count > 30, "Spline loop has sufficient interpolated steps");

            Mesh mesh = RoadMeshBuilder.GenerateRibbonMesh(spline, 8f);
            Assert(mesh != null, "Ribbon loop mesh generated");
            AssertEqual(spline.Count * 2, mesh.vertices.Length, "Vertex count matches points");
        }

        #endregion

        #region Group 6: Extreme Stress & Scale Fuzzing

        private static void Test_Scale_LargeBuildingCountBatching()
        {
            // Synthesize large manifest with 500 buildings
            var manifest = new WorldManifest();
            var zone = new ZoneManifest { id = "z_large", faction = "B", destruction = "03" };
            manifest.zones.Add(zone);

            for (int i = 0; i < 500; i++)
            {
                manifest.buildings.Add(new BuildingManifest
                {
                    id = $"bld_{i}",
                    zone_id = "z_large",
                    prefab_name = "SM_Bld_Tent_01",
                    position = new float[] { i * 5f, 0f, (i % 10) * 10f },
                    rotation = new float[] { 0f, (i * 30) % 360, 0f },
                    scale = new float[] { 1f, 1f, 1f },
                    bounding_box = new BoundingBoxManifest { size = new float[] { 7.8f, 4.1f, 12f } }
                });
            }

            var rootGO = new GameObject("Root");
            for (int i = 0; i < manifest.buildings.Count; i++)
            {
                var go = PrefabSpawner.SpawnBuilding(manifest.buildings[i], zone, rootGO.transform, "NonExistentDir");
                Assert(go != null, $"Building {i} spawned");
            }
            AssertEqual(500, rootGO.transform.childCount, "500 buildings successfully instantiated");
        }

        private static void Test_TypeCoercion_StringIntegersAndFloatResolutions()
        {
            string coercedJson = @"{
                ""metadata"": {
                    ""seed"": ""1337""
                },
                ""terrain"": {
                    ""resolution"": ""257"",
                    ""width"": ""1200.5"",
                    ""length"": ""1200.5"",
                    ""height_scale"": ""180.0"",
                    ""world_size"": [""1200.5"", ""180.0"", ""1200.5""]
                },
                ""zones"": [
                    {
                        ""id"": ""zone_str"",
                        ""radius"": ""75.5"",
                        ""density"": ""0.85""
                    }
                ],
                ""roads"": [
                    {
                        ""id"": ""road_str"",
                        ""width"": ""12.5""
                    }
                ]
            }";

            WorldManifest manifest = ManifestJsonParser.Parse(coercedJson);
            AssertEqual(1337, manifest.metadata.seed, "String seed '1337' converted to int 1337");
            AssertEqual(257, manifest.terrain.resolution, "String resolution '257' converted to int 257");
            AssertApproxEqual(1200.5f, manifest.terrain.width, 0.01f, "Direct string width converted to float");
            AssertApproxEqual(1200.5f, manifest.terrain.GetWidth(), 0.01f, "String world_size array converted to float");
            AssertApproxEqual(75.5f, manifest.zones[0].radius, 0.01f, "String radius converted to float");
            AssertApproxEqual(12.5f, manifest.roads[0].width, 0.01f, "String road width converted to float");
        }

        private static void Test_Terrain_InvertedMinMaxElevationManifest()
        {
            var manifest = new TerrainManifest
            {
                min_height = 500f,
                max_height = 0f, // Inverted min > max
                height_scale = 150f,
                raw_heightmap_2d = new float[,]
                {
                    { 50f, 100f },
                    { 25f, 75f }
                }
            };

            float[,] resampled = TerrainGenerator.ResampleHeightmap(manifest, 65, 150f);
            for (int z = 0; z < 65; z++)
            {
                for (int x = 0; x < 65; x++)
                {
                    float h = resampled[z, x];
                    Assert(h >= 0.0f && h <= 1.0f, "Normalized height valid despite inverted min/max metadata");
                }
            }
        }

        private static void Test_Road_AcuteZigzagAndSharpHairpins()
        {
            var zigzagWaypoints = new List<float[]>
            {
                new float[] { 0f, 0f, 0f },
                new float[] { 50f, 0f, 50f },
                new float[] { 0f, 0f, 55f }, // Sharp 170-degree acute turn
                new float[] { 50f, 0f, 105f },
                new float[] { 0f, 0f, 110f }
            };

            var road = new RoadManifest
            {
                id = "road_zigzag",
                width = 6.0f,
                waypoints = zigzagWaypoints
            };

            var roadGO = RoadMeshBuilder.BuildRoad(road, null, null, true, true);
            Assert(roadGO != null, "Zigzag road generated");
            MeshFilter mf = roadGO.GetComponent<MeshFilter>();
            Assert(mf != null && mf.sharedMesh != null, "MeshFilter sharedMesh exists");
            foreach (var v in mf.sharedMesh.vertices)
            {
                Assert(!float.IsNaN(v.x) && !float.IsNaN(v.y) && !float.IsNaN(v.z), "Vertices contain no NaNs during sharp turns");
            }
        }

        private static void Test_AdaptiveMesh_EmptyOrDegenerateMeshData()
        {
            // Null mesh
            var nullManifest = new TerrainManifest { mesh = null };
            Assert(AdaptiveMeshGenerator.BuildAdaptiveMesh(nullManifest, null) == null, "Null mesh should return null");

            // Empty vertices mesh
            var emptyManifest = new TerrainManifest { mesh = new MeshDataManifest() };
            Assert(AdaptiveMeshGenerator.BuildAdaptiveMesh(emptyManifest, null) == null, "Empty mesh data should return null");
        }

        private static void Test_AdaptiveMesh_FlatArrayLengthNotMultipleOfThree()
        {
            var manifest = new TerrainManifest
            {
                width = 100f,
                length = 100f,
                height_scale = 50f,
                mesh = new MeshDataManifest
                {
                    flat_vertices = new float[] { 0f, 1f, 2f, 3f, 4f }, // 5 elements -> only 1 complete vertex
                    flat_indices = new int[] { 0, 0, 0 }
                }
            };

            GameObject go = AdaptiveMeshGenerator.BuildAdaptiveMesh(manifest, null);
            Assert(go != null, "Building adaptive mesh with non-multiple flat vertices does not crash");
            MeshFilter mf = go.GetComponent<MeshFilter>();
            AssertEqual(1, mf.sharedMesh.vertexCount, "Vertex count is 1");
        }

        private static void Test_AdaptiveMesh_MissingNormalsAndUVsFallback()
        {
            var manifest = new TerrainManifest
            {
                width = 200f,
                length = 200f,
                height_scale = 100f,
                mesh = new MeshDataManifest
                {
                    vertices = new List<float[]>
                    {
                        new float[] { 0f, 0f, 0f },
                        new float[] { 200f, 10f, 0f },
                        new float[] { 0f, 20f, 200f }
                    },
                    indices = new List<int> { 0, 1, 2 }
                    // Normals and UVs are explicitly null
                }
            };

            GameObject go = AdaptiveMeshGenerator.BuildAdaptiveMesh(manifest, null);
            Assert(go != null, "Adaptive mesh generated without provided normals/UVs");
            MeshFilter mf = go.GetComponent<MeshFilter>();
            Assert(mf.sharedMesh.normals != null && mf.sharedMesh.normals.Length == 3, "Normals automatically calculated");
            Assert(mf.sharedMesh.uv != null && mf.sharedMesh.uv.Length == 3, "UVs automatically normalized");
            foreach (var uv in mf.sharedMesh.uv)
            {
                Assert(uv.x >= 0f && uv.x <= 1f && uv.y >= 0f && uv.y <= 1f, "Fallback UVs clamped in [0, 1]");
            }
        }

        private static void Test_TemplatedZone_NullDistrictAndOrphanedPlacementRole()
        {
            var z = new ZoneManifest { id = "z_test", name = "Test Zone" };
            var bldNull = new BuildingManifest { id = "b_null", prefab_name = "SM_Bld_Tent_01", district_id = null, placement_role = null };
            var bldRoleOnly = new BuildingManifest { id = "b_role", prefab_name = "SM_Bld_Tent_01", district_id = null, placement_role = "perimeter_watch" };

            var zGO = new GameObject("Zone_z_test");
            var dRole = new GameObject("District_perimeter_watch");
            dRole.transform.SetParent(zGO.transform);

            var spawnedNull = PrefabSpawner.SpawnBuilding(bldNull, z, zGO.transform, "Assets/PolygonMilitary/Prefabs");
            var spawnedRole = PrefabSpawner.SpawnBuilding(bldRoleOnly, z, dRole.transform, "Assets/PolygonMilitary/Prefabs");

            Assert(spawnedNull != null && spawnedRole != null, "Buildings with null districts spawned successfully");
            AssertEqual(zGO.transform, spawnedNull.transform.parent, "Null district building parented directly to zone");
            AssertEqual(dRole.transform, spawnedRole.transform.parent, "Role district building parented to role district");
        }

        private static void Test_AdaptiveMesh_32BitLargeMeshStress()
        {
            int vertCount = 100000;
            var manifest = new TerrainManifest
            {
                width = 5000f,
                length = 5000f,
                height_scale = 500f,
                mesh = new MeshDataManifest
                {
                    vertex_count = vertCount
                }
            };

            for (int i = 0; i < vertCount; i++)
            {
                manifest.mesh.vertices.Add(new float[] { (i % 300) * 15f, (i / 300) * 0.2f, (i / 300) * 15f });
            }
            manifest.mesh.indices.AddRange(new int[] { 0, 1, 2, 99997, 99998, 99999 });

            GameObject go = AdaptiveMeshGenerator.BuildAdaptiveMesh(manifest, null);
            Assert(go != null, "100k vertex mesh instantiated");
            MeshFilter mf = go.GetComponent<MeshFilter>();
            AssertEqual(UnityEngine.Rendering.IndexFormat.UInt32, mf.sharedMesh.indexFormat, "IndexFormat configured to UInt32");
            AssertEqual(vertCount, mf.sharedMesh.vertexCount, "Vertex count is 100k");
            Assert(!float.IsNaN(mf.sharedMesh.bounds.size.x), "Bounds calculated without NaN");
        }

        private static void Test_AdaptiveMesh_MalformedJsonWithMixedNullAttributes()
        {
            string malformedJson = @"{
                ""terrain"": {
                    ""mesh"": {
                        ""vertex_count"": 3,
                        ""vertices"": [
                            [0.0, 0.0, 0.0],
                            null,
                            [10.0, 5.0, 10.0]
                        ],
                        ""indices"": [0, 1, 2],
                        ""normals"": null,
                        ""uvs"": [null, [0.5, 0.5]]
                    }
                }
            }";

            WorldManifest manifest = ManifestJsonParser.Parse(malformedJson);
            Assert(manifest.terrain.mesh != null, "Mesh parsed from malformed JSON");
            GameObject go = AdaptiveMeshGenerator.BuildAdaptiveMesh(manifest.terrain, null);
            Assert(go != null, "Built mesh safely despite null vertices and null UV entries");
        }

        #endregion
    }
}
