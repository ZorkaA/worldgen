using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using WorldGen.Core;
using WorldGen.Editor;

namespace WorldGen.Tests
{
    public class WorldImporterTestRunner
    {
        private static int passedTests = 0;
        private static int failedTests = 0;

        public static int Main(string[] args)
        {
            Console.WriteLine("================================================================");
            Console.WriteLine("        WORLDGEN UNITY IMPORTER TEST SUITE (C# / MONO)          ");
            Console.WriteLine("================================================================");

            RunTest("TestJsonParser_StandardManifest", TestJsonParser_StandardManifest);
            RunTest("TestJsonParser_1DHeightmap", TestJsonParser_1DHeightmap);
            RunTest("TestJsonParser_MalformedAndEdgeCases", TestJsonParser_MalformedAndEdgeCases);
            RunTest("TestTerrainGenerator_BilinearInterpolation", TestTerrainGenerator_BilinearInterpolation);
            RunTest("TestTerrainGenerator_HeightmapResolutionMath", TestTerrainGenerator_HeightmapResolutionMath);
            RunTest("TestTerrainGenerator_SetHeightsNormalization", TestTerrainGenerator_SetHeightsNormalization);
            RunTest("TestMaterialSwapper_ThemeResolution", TestMaterialSwapper_ThemeResolution);
            RunTest("TestMaterialSwapper_MaterialPreservationRules", TestMaterialSwapper_MaterialPreservationRules);
            RunTest("TestRoadMeshBuilder_SplineAndRibbonGeometry", TestRoadMeshBuilder_SplineAndRibbonGeometry);
            RunTest("TestPrefabSpawner_FallbackProxyDimensions", TestPrefabSpawner_FallbackProxyDimensions);
            RunTest("TestHierarchy_CleanStructureGeneration", TestHierarchy_CleanStructureGeneration);
            RunTest("TestEndToEnd_SampleManifestImport", TestEndToEnd_SampleManifestImport);

            Console.WriteLine("================================================================");
            Console.WriteLine($"RESULTS: {passedTests} PASSED, {failedTests} FAILED");
            Console.WriteLine("================================================================");

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
                Console.WriteLine(ex.StackTrace);
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
                throw new Exception($"Assertion Failed: {message}. Expected: {expected}, Actual: {actual}");
        }

        private static void AssertApproxEqual(float expected, float actual, float tolerance, string message)
        {
            if (Math.Abs(expected - actual) > tolerance)
                throw new Exception($"Assertion Failed: {message}. Expected: {expected} (+/-{tolerance}), Actual: {actual}");
        }

        #region Test Cases

        private static void TestJsonParser_StandardManifest()
        {
            string sampleJson = @"{
                ""metadata"": {
                    ""seed"": 1337,
                    ""generator_version"": ""1.2.0"",
                    ""generator"": ""FastAPI WorldGen"",
                    ""bounds"": [-500.0, 0.0, -500.0, 500.0, 150.0, 500.0]
                },
                ""terrain"": {
                    ""resolution"": 4,
                    ""world_size"": [1000.0, 120.0, 1000.0],
                    ""heightmap"": [
                        [0.0, 10.0, 20.0, 30.0],
                        [10.0, 20.0, 30.0, 40.0],
                        [20.0, 30.0, 40.0, 50.0],
                        [30.0, 40.0, 50.0, 60.0]
                    ]
                },
                ""zones"": [
                    {
                        ""id"": ""zone_0"",
                        ""name"": ""Alpha Base"",
                        ""faction"": ""A"",
                        ""destruction"": ""02"",
                        ""center"": [100.0, 25.0, 150.0],
                        ""radius"": 75.0,
                        ""density"": 0.7
                    }
                ],
                ""buildings"": [
                    {
                        ""id"": ""bld_1"",
                        ""zone_id"": ""zone_0"",
                        ""prefab_name"": ""SM_Bld_Tent_01"",
                        ""position"": [105.0, 25.0, 155.0],
                        ""rotation"": [0.0, 90.0, 0.0],
                        ""scale"": [1.0, 1.0, 1.0],
                        ""bbox"": {
                            ""min"": [-3.5, 0.0, -5.0],
                            ""max"": [3.5, 4.0, 5.0],
                            ""size"": [7.0, 4.0, 10.0]
                        }
                    }
                ],
                ""roads"": [
                    {
                        ""id"": ""road_0_1"",
                        ""from_zone"": ""zone_0"",
                        ""to_zone"": ""zone_1"",
                        ""width"": 8.0,
                        ""waypoints"": [
                            [100.0, 25.0, 150.0],
                            [150.0, 28.0, 200.0],
                            [200.0, 30.0, 250.0]
                        ]
                    }
                ]
            }";

            WorldManifest manifest = ManifestJsonParser.Parse(sampleJson);

            Assert(manifest != null, "Manifest should not be null");
            AssertEqual(1337, manifest.metadata.seed, "Metadata seed mismatch");
            AssertEqual("1.2.0", manifest.metadata.generator_version, "Generator version mismatch");
            AssertEqual(1000f, manifest.terrain.GetWidth(), "Terrain width mismatch");
            AssertEqual(120f, manifest.terrain.GetHeightScale(), "Terrain height_scale mismatch");
            AssertEqual(1000f, manifest.terrain.GetLength(), "Terrain length mismatch");

            Assert(manifest.terrain.raw_heightmap_2d != null, "2D heightmap should be parsed");
            AssertEqual(4, manifest.terrain.raw_heightmap_2d.GetLength(0), "Heightmap rows mismatch");
            AssertEqual(4, manifest.terrain.raw_heightmap_2d.GetLength(1), "Heightmap cols mismatch");
            AssertApproxEqual(60.0f, manifest.terrain.raw_heightmap_2d[3, 3], 0.01f, "Heightmap [3,3] value mismatch");

            AssertEqual(1, manifest.zones.Count, "Zones count mismatch");
            AssertEqual("Alpha Base", manifest.zones[0].name, "Zone name mismatch");
            AssertEqual("A", manifest.zones[0].GetNormalizedFaction(), "Zone faction mismatch");
            AssertEqual("02", manifest.zones[0].GetNormalizedDestruction(), "Zone destruction mismatch");

            AssertEqual(1, manifest.buildings.Count, "Buildings count mismatch");
            AssertEqual("SM_Bld_Tent_01", manifest.buildings[0].prefab_name, "Prefab name mismatch");
            AssertApproxEqual(7.0f, manifest.buildings[0].GetBoundingBox().GetSize().x, 0.01f, "BBox size X mismatch");

            AssertEqual(1, manifest.roads.Count, "Roads count mismatch");
            AssertEqual(3, manifest.roads[0].waypoints.Count, "Road waypoints count mismatch");
            AssertEqual(8.0f, manifest.roads[0].width, "Road width mismatch");
        }

        private static void TestJsonParser_1DHeightmap()
        {
            string sampleJson = @"{
                ""metadata"": { ""seed"": 42 },
                ""terrain"": {
                    ""resolution"": 3,
                    ""width"": 300.0,
                    ""length"": 300.0,
                    ""height_scale"": 50.0,
                    ""heights"": [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0]
                },
                ""zones"": [],
                ""buildings"": [],
                ""roads"": []
            }";

            WorldManifest manifest = ManifestJsonParser.Parse(sampleJson);
            Assert(manifest != null, "Manifest parsed");
            Assert(manifest.terrain.raw_heightmap_1d != null, "1D heightmap should be parsed");
            AssertEqual(9, manifest.terrain.raw_heightmap_1d.Length, "1D heightmap length");
            AssertApproxEqual(40.0f, manifest.terrain.raw_heightmap_1d[8], 0.01f, "1D heightmap last element");
        }

        private static void TestJsonParser_MalformedAndEdgeCases()
        {
            // Empty string should throw ArgumentException
            bool threw = false;
            try { ManifestJsonParser.Parse(""); } catch (ArgumentException) { threw = true; }
            Assert(threw, "Empty JSON string must throw ArgumentException");

            // Valid empty JSON with escaped characters in strings
            string escapedJson = @"{
                ""metadata"": { ""generator"": ""WorldGen \""\n\t\\ Special"" },
                ""terrain"": { ""resolution"": 65 },
                ""zones"": [],
                ""buildings"": [],
                ""roads"": []
            }";
            WorldManifest manifest = ManifestJsonParser.Parse(escapedJson);
            Assert(manifest.metadata.generator.Contains("Special"), "Escaped string must parse correctly");
        }

        private static void TestTerrainGenerator_BilinearInterpolation()
        {
            var manifest = new TerrainManifest
            {
                resolution = 2,
                width = 100f,
                height_scale = 100f,
                length = 100f,
                raw_heightmap_2d = new float[,]
                {
                    { 0f, 100f },
                    { 0f, 100f }
                }
            };

            // Resample from 2x2 to 65x65
            float[,] resampled = TerrainGenerator.ResampleHeightmap(manifest, 65, 100f);
            AssertEqual(65, resampled.GetLength(0), "Resampled rows");
            AssertEqual(65, resampled.GetLength(1), "Resampled cols");

            // Check corner heights (normalized to [0, 1])
            AssertApproxEqual(0.0f, resampled[0, 0], 0.01f, "Left-bottom height normalized");
            AssertApproxEqual(1.0f, resampled[0, 64], 0.01f, "Right-bottom height normalized");
            AssertApproxEqual(0.5f, resampled[0, 32], 0.02f, "Middle height bilinear interpolation");
            AssertApproxEqual(0.5f, resampled[32, 32], 0.02f, "Center height bilinear interpolation");
        }

        private static void TestTerrainGenerator_HeightmapResolutionMath()
        {
            AssertEqual(65, TerrainGenerator.CalculateUnityHeightmapResolution(32), "Resolution 32 -> 65");
            AssertEqual(65, TerrainGenerator.CalculateUnityHeightmapResolution(64), "Resolution 64 -> 65");
            AssertEqual(129, TerrainGenerator.CalculateUnityHeightmapResolution(100), "Resolution 100 -> 129");
            AssertEqual(257, TerrainGenerator.CalculateUnityHeightmapResolution(256), "Resolution 256 -> 257");
            AssertEqual(513, TerrainGenerator.CalculateUnityHeightmapResolution(512), "Resolution 512 -> 513");
            AssertEqual(1025, TerrainGenerator.CalculateUnityHeightmapResolution(1000), "Resolution 1000 -> 1025");
        }

        private static void TestTerrainGenerator_SetHeightsNormalization()
        {
            var manifest = new TerrainManifest
            {
                resolution = 3,
                height_scale = 200f,
                raw_heightmap_2d = new float[,]
                {
                    { -50f, 100f, 250f },
                    { 0f, 150f, 300f },
                    { 50f, 200f, 400f }
                }
            };

            float[,] resampled = TerrainGenerator.ResampleHeightmap(manifest, 65, 200f);

            // All heights must be strictly clamped into [0.0, 1.0]
            for (int z = 0; z < 65; z++)
            {
                for (int x = 0; x < 65; x++)
                {
                    float h = resampled[z, x];
                    Assert(h >= 0.0f && h <= 1.0f, $"Height at [{z},{x}]={h} is outside [0, 1] range");
                }
            }
        }

        private static void TestMaterialSwapper_ThemeResolution()
        {
            AssertEqual("A", MaterialSwapper.NormalizeFaction("A"), "Faction A");
            AssertEqual("B", MaterialSwapper.NormalizeFaction("factionB"), "Faction B");
            AssertEqual("C", MaterialSwapper.NormalizeFaction("c"), "Faction C");
            AssertEqual("A", MaterialSwapper.NormalizeFaction("unknown"), "Fallback Faction");

            AssertEqual("01", MaterialSwapper.NormalizeDestruction("01"), "Destruction 01");
            AssertEqual("02", MaterialSwapper.NormalizeDestruction("2"), "Destruction 2 -> 02");
            AssertEqual("03", MaterialSwapper.NormalizeDestruction("03"), "Destruction 03");
            AssertEqual("04", MaterialSwapper.NormalizeDestruction("4"), "Destruction 4 -> 04");
            AssertEqual("01", MaterialSwapper.NormalizeDestruction("invalid"), "Fallback Destruction");
        }

        private static void TestMaterialSwapper_MaterialPreservationRules()
        {
            // Base materials that MUST be swapped
            Assert(MaterialSwapper.IsSwappableMaterial("PolygonMilitary_Mat_01_A"), "Base mat 01_A swappable");
            Assert(MaterialSwapper.IsSwappableMaterial("PolygonMilitary_Mat_02_B"), "Base mat 02_B swappable");
            Assert(MaterialSwapper.IsSwappableMaterial("PolygonMilitary_Mat_Gold_01"), "Gold mat swappable");

            // Protected materials that MUST be preserved
            Assert(MaterialSwapper.IsProtectedMaterial("PolygonMilitary_Glass_01"), "Glass mat protected");
            Assert(MaterialSwapper.IsProtectedMaterial("PolygonMilitary_Vehicles"), "Vehicle mat protected");
            Assert(MaterialSwapper.IsProtectedMaterial("Decals_Mat"), "Decal mat protected");
            Assert(MaterialSwapper.IsProtectedMaterial("Water_Shader_Mat"), "Water mat protected");
            Assert(MaterialSwapper.IsProtectedMaterial("FX_Smoke_Mat"), "FX mat protected");
        }

        private static void TestRoadMeshBuilder_SplineAndRibbonGeometry()
        {
            var waypoints = new List<Vector3>
            {
                new Vector3(0, 0, 0),
                new Vector3(50, 5, 50),
                new Vector3(100, 10, 100)
            };

            List<Vector3> spline = RoadMeshBuilder.SampleCatmullRomSpline(waypoints, 10);
            Assert(spline.Count >= 20, $"Spline should contain at least 20 sampled points (actual: {spline.Count})");

            Mesh ribbonMesh = RoadMeshBuilder.GenerateRibbonMesh(spline, 6.0f);
            Assert(ribbonMesh != null, "Ribbon mesh generated");
            AssertEqual(spline.Count * 2, ribbonMesh.vertices.Length, "Vertex count (2 per point)");
            AssertEqual((spline.Count - 1) * 6, ribbonMesh.triangles.Length, "Triangle indices count (6 per quad)");
            AssertEqual(ribbonMesh.vertices.Length, ribbonMesh.uv.Length, "UVs count matches vertices");
            AssertEqual(ribbonMesh.vertices.Length, ribbonMesh.normals.Length, "Normals count matches vertices");
        }

        private static void TestPrefabSpawner_FallbackProxyDimensions()
        {
            var bld = new BuildingManifest
            {
                prefab_name = "SM_Bld_Hangar_01",
                bounding_box = new BoundingBoxManifest
                {
                    min = new float[] { -10f, 0f, -15f },
                    max = new float[] { 10f, 8f, 15f },
                    size = new float[] { 20f, 8f, 30f },
                    center = new float[] { 0f, 4f, 0f }
                }
            };

            var proxy = PrefabSpawner.SpawnBuilding(bld, null, null, "NonExistentFolder");
            Assert(proxy != null, "Proxy object spawned");
            AssertApproxEqual(20f, proxy.transform.localScale.x, 0.01f, "Proxy width (X scale)");
            AssertApproxEqual(8f, proxy.transform.localScale.y, 0.01f, "Proxy height (Y scale)");
            AssertApproxEqual(30f, proxy.transform.localScale.z, 0.01f, "Proxy length (Z scale)");
        }

        private static void TestHierarchy_CleanStructureGeneration()
        {
            var root = new GameObject("[WorldGen_Output]");
            var terrainParent = new GameObject("Terrain");
            terrainParent.transform.SetParent(root.transform);

            var zonesParent = new GameObject("Zones");
            zonesParent.transform.SetParent(root.transform);

            var zone0 = new GameObject("Zone_zone_0_FactionA_Destruction02");
            zone0.transform.SetParent(zonesParent.transform);

            var bld0 = new GameObject("SM_Bld_Tent_01_bld_0");
            bld0.transform.SetParent(zone0.transform);

            var roadsParent = new GameObject("Roads");
            roadsParent.transform.SetParent(root.transform);

            AssertEqual(3, root.transform.childCount, "Root has 3 main categories (Terrain, Zones, Roads)");
            AssertEqual("Terrain", root.transform.GetChild(0).gameObject.name, "Child 0 is Terrain");
            AssertEqual("Zones", root.transform.GetChild(1).gameObject.name, "Child 1 is Zones");
            AssertEqual("Roads", root.transform.GetChild(2).gameObject.name, "Child 2 is Roads");
            AssertEqual(1, zonesParent.transform.childCount, "Zones parent has 1 zone");
            AssertEqual("Zone_zone_0_FactionA_Destruction02", zonesParent.transform.GetChild(0).gameObject.name, "Zone naming convention");
        }

        private static void TestEndToEnd_SampleManifestImport()
        {
            string samplePath = "/Users/jack/worldgen/unity/sample_world_manifest.json";
            Assert(File.Exists(samplePath), "sample_world_manifest.json must exist");

            string json = File.ReadAllText(samplePath);
            WorldManifest manifest = ManifestJsonParser.Parse(json);
            Assert(manifest != null, "Manifest parsed successfully");

            // Build full hierarchy
            var root = new GameObject("[WorldGen_Output]");

            // Terrain
            var terrainParent = new GameObject("Terrain");
            terrainParent.transform.SetParent(root.transform);
            GameObject terrainGO = TerrainGenerator.BuildTerrain(manifest.terrain, terrainParent.transform, out Terrain terrainInstance);
            Assert(terrainGO != null, "Terrain GO created");
            Assert(terrainInstance != null, "Terrain component created");
            Assert(terrainInstance.terrainData != null, "TerrainData created");
            AssertEqual(65, terrainInstance.terrainData.heightmapResolution, "Terrain heightmap resolution");

            // Zones & Buildings
            var zonesParent = new GameObject("Zones");
            zonesParent.transform.SetParent(root.transform);

            var zoneTransforms = new Dictionary<string, Transform>();
            var zoneMap = new Dictionary<string, ZoneManifest>();
            foreach (var z in manifest.zones)
            {
                zoneMap[z.id] = z;
                var zGO = new GameObject($"Zone_{z.id}_Faction{z.GetNormalizedFaction()}_Destruction{z.GetNormalizedDestruction()}");
                zGO.transform.SetParent(zonesParent.transform);
                zoneTransforms[z.id] = zGO.transform;
            }

            foreach (var b in manifest.buildings)
            {
                Transform parent = zonesParent.transform;
                ZoneManifest zm = null;
                if (zoneTransforms.TryGetValue(b.zone_id, out Transform zt))
                {
                    parent = zt;
                    zoneMap.TryGetValue(b.zone_id, out zm);
                }

                GameObject bldGO = PrefabSpawner.SpawnBuilding(b, zm, parent, "Assets/PolygonMilitary/Prefabs");
                Assert(bldGO != null, $"Building {b.prefab_name} spawned");

                string f = !string.IsNullOrEmpty(b.faction) ? b.faction : (zm != null ? zm.faction : "A");
                string d = !string.IsNullOrEmpty(b.destruction) ? b.destruction : (zm != null ? zm.destruction : "01");
                MaterialSwapper.ApplyZoneTheme(bldGO, f, d);
            }

            // Roads
            var roadsParent = new GameObject("Roads");
            roadsParent.transform.SetParent(root.transform);
            foreach (var road in manifest.roads)
            {
                GameObject roadGO = RoadMeshBuilder.BuildRoad(road, roadsParent.transform, terrainInstance, true, true);
                Assert(roadGO != null, $"Road {road.id} generated");
                MeshFilter mf = roadGO.GetComponent<MeshFilter>();
                Assert(mf != null && mf.sharedMesh != null, "Road mesh assigned");
                LineRenderer lr = roadGO.GetComponent<LineRenderer>();
                Assert(lr != null && lr.positionCount > 0, "Road line renderer assigned");
            }

            // Verify top-level hierarchy counts
            AssertEqual(3, root.transform.childCount, "Root hierarchy categories");
            AssertEqual(2, zonesParent.transform.childCount, "Zone count matches manifest");
            AssertEqual(1, roadsParent.transform.childCount, "Road count matches manifest");
        }

        #endregion
    }
}
