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
            RunTest("TestAdaptiveMeshGenerator_VariableDensityMeshCreation", TestAdaptiveMeshGenerator_VariableDensityMeshCreation);
            RunTest("TestAdaptiveMeshGenerator_32BitIndexBufferConfiguration", TestAdaptiveMeshGenerator_32BitIndexBufferConfiguration);
            RunTest("TestJsonParser_AdaptiveMeshFlatAndNestedArrays", TestJsonParser_AdaptiveMeshFlatAndNestedArrays);
            RunTest("TestTemplatedZone_SubDistrictHierarchyAndZoneMetadata", TestTemplatedZone_SubDistrictHierarchyAndZoneMetadata);
            RunTest("TestTerrainMode_DualModeExecution", TestTerrainMode_DualModeExecution);
            RunTest("TestEndToEnd_AdaptiveMeshSampleImport", TestEndToEnd_AdaptiveMeshSampleImport);

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

        private static void TestAdaptiveMeshGenerator_VariableDensityMeshCreation()
        {
            var manifest = new TerrainManifest
            {
                width = 500f,
                length = 500f,
                height_scale = 100f,
                mesh = new MeshDataManifest
                {
                    vertices = new List<float[]>
                    {
                        new float[] { 0f, 0f, 0f },
                        new float[] { 250f, 5f, 0f },
                        new float[] { 500f, 10f, 0f },
                        new float[] { 0f, 5f, 250f },
                        new float[] { 250f, 40f, 250f }, // Slope peak
                        new float[] { 500f, 15f, 250f },
                        new float[] { 0f, 10f, 500f },
                        new float[] { 500f, 20f, 500f }
                    },
                    indices = new List<int>
                    {
                        0, 1, 3,  1, 4, 3,
                        1, 2, 4,  2, 5, 4,
                        3, 4, 6,  4, 5, 7
                    },
                    normals = new List<float[]>
                    {
                        new float[] { 0f, 1f, 0f },
                        new float[] { 0f, 0.95f, 0.1f },
                        new float[] { 0f, 1f, 0f },
                        new float[] { 0.1f, 0.9f, 0f },
                        new float[] { 0f, 0.8f, 0.6f },
                        new float[] { -0.1f, 0.9f, 0f },
                        new float[] { 0f, 1f, 0f },
                        new float[] { 0f, 1f, 0f }
                    },
                    uvs = new List<float[]>
                    {
                        new float[] { 0f, 0f },
                        new float[] { 0.5f, 0f },
                        new float[] { 1f, 0f },
                        new float[] { 0f, 0.5f },
                        new float[] { 0.5f, 0.5f },
                        new float[] { 1f, 0.5f },
                        new float[] { 0f, 1f },
                        new float[] { 1f, 1f }
                    }
                }
            };

            var parent = new GameObject("TerrainRoot");
            GameObject meshGO = AdaptiveMeshGenerator.BuildAdaptiveMesh(manifest, parent.transform);

            Assert(meshGO != null, "AdaptiveTerrainMesh GameObject must be instantiated");
            AssertEqual("AdaptiveTerrainMesh", meshGO.name, "GameObject name matches AdaptiveTerrainMesh");
            AssertEqual(parent.transform, meshGO.transform.parent, "Mesh parented under TerrainRoot");

            MeshFilter mf = meshGO.GetComponent<MeshFilter>();
            Assert(mf != null, "MeshFilter attached");
            Assert(mf.sharedMesh != null, "Mesh attached to MeshFilter");
            AssertEqual(8, mf.sharedMesh.vertices.Length, "Vertex count matches 8");
            AssertEqual(18, mf.sharedMesh.triangles.Length, "Triangle indices count matches 18 (6 triangles)");

            MeshRenderer mr = meshGO.GetComponent<MeshRenderer>();
            Assert(mr != null, "MeshRenderer attached");
            Assert(mr.sharedMaterial != null, "Material attached to MeshRenderer");

            MeshCollider mc = meshGO.GetComponent<MeshCollider>();
            Assert(mc != null, "MeshCollider attached");
            AssertEqual(mf.sharedMesh, mc.sharedMesh, "MeshCollider sharedMesh matches MeshFilter sharedMesh");
        }

        private static void TestAdaptiveMeshGenerator_32BitIndexBufferConfiguration()
        {
            // Case 1: Large mesh (> 65,535 vertices) -> must configure IndexFormat.UInt32
            int largeVertCount = 70000;
            var largeManifest = new TerrainManifest
            {
                width = 2000f,
                length = 2000f,
                height_scale = 200f,
                mesh = new MeshDataManifest
                {
                    vertex_count = largeVertCount
                }
            };
            for (int i = 0; i < largeVertCount; i++)
            {
                largeManifest.mesh.vertices.Add(new float[] { (i % 200) * 10f, (i / 200) * 0.5f, (i / 200) * 10f });
            }
            largeManifest.mesh.indices.AddRange(new int[] { 0, 1, 2, 65536, 65537, 65538 });

            GameObject largeMeshGO = AdaptiveMeshGenerator.BuildAdaptiveMesh(largeManifest, null);
            Assert(largeMeshGO != null, "Large mesh GameObject instantiated");
            MeshFilter largeMf = largeMeshGO.GetComponent<MeshFilter>();
            Assert(largeMf != null && largeMf.sharedMesh != null, "Large mesh created");
            AssertEqual(UnityEngine.Rendering.IndexFormat.UInt32, largeMf.sharedMesh.indexFormat, "32-bit IndexFormat configured for >65,535 vertices");

            // Case 2: Small mesh (<= 65,535 vertices) -> IndexFormat.UInt16 default
            var smallManifest = new TerrainManifest
            {
                width = 500f,
                length = 500f,
                height_scale = 100f,
                mesh = new MeshDataManifest
                {
                    vertices = new List<float[]>
                    {
                        new float[] { 0f, 0f, 0f },
                        new float[] { 100f, 0f, 0f },
                        new float[] { 0f, 0f, 100f }
                    },
                    indices = new List<int> { 0, 1, 2 }
                }
            };
            GameObject smallMeshGO = AdaptiveMeshGenerator.BuildAdaptiveMesh(smallManifest, null);
            MeshFilter smallMf = smallMeshGO.GetComponent<MeshFilter>();
            AssertEqual(UnityEngine.Rendering.IndexFormat.UInt16, smallMf.sharedMesh.indexFormat, "16-bit IndexFormat used for small meshes");
        }

        private static void TestJsonParser_AdaptiveMeshFlatAndNestedArrays()
        {
            // 1. Nested arrays JSON
            string nestedJson = @"{
                ""terrain"": {
                    ""resolution"": 257,
                    ""world_size"": [1000.0, 150.0, 1000.0],
                    ""mesh"": {
                        ""vertex_count"": 4,
                        ""triangle_count"": 2,
                        ""decimation_ratio"": 0.25,
                        ""vertices"": [
                            [0.0, 0.0, 0.0],
                            [1000.0, 0.0, 0.0],
                            [0.0, 50.0, 1000.0],
                            [1000.0, 50.0, 1000.0]
                        ],
                        ""indices"": [0, 1, 2, 1, 3, 2],
                        ""normals"": [
                            [0.0, 1.0, 0.0],
                            [0.0, 1.0, 0.0],
                            [0.0, 0.9, -0.1],
                            [0.0, 0.9, -0.1]
                        ],
                        ""uvs"": [
                            [0.0, 0.0],
                            [1.0, 0.0],
                            [0.0, 1.0],
                            [1.0, 1.0]
                        ]
                    }
                },
                ""zones"": [],
                ""buildings"": [],
                ""roads"": []
            }";

            WorldManifest manifestNested = ManifestJsonParser.Parse(nestedJson);
            Assert(manifestNested.terrain.mesh != null, "Nested mesh parsed");
            AssertEqual(4, manifestNested.terrain.mesh.vertices.Count, "Nested vertices count");
            AssertEqual(6, manifestNested.terrain.mesh.indices.Count, "Nested indices count");
            AssertApproxEqual(1000.0f, manifestNested.terrain.mesh.vertices[1][0], 0.01f, "Nested vertex [1].x");

            // 2. Flat arrays JSON
            string flatJson = @"{
                ""terrain"": {
                    ""resolution"": 257,
                    ""world_size"": [1000.0, 150.0, 1000.0],
                    ""mesh"": {
                        ""vertex_count"": 4,
                        ""triangle_count"": 2,
                        ""vertices"": [0.0, 0.0, 0.0, 1000.0, 0.0, 0.0, 0.0, 50.0, 1000.0, 1000.0, 50.0, 1000.0],
                        ""indices"": [0, 1, 2, 1, 3, 2],
                        ""normals"": [0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.9, -0.1, 0.0, 0.9, -0.1],
                        ""uvs"": [0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0]
                    }
                },
                ""zones"": [],
                ""buildings"": [],
                ""roads"": []
            }";

            WorldManifest manifestFlat = ManifestJsonParser.Parse(flatJson);
            Assert(manifestFlat.terrain.mesh != null, "Flat mesh parsed");
            AssertEqual(4, manifestFlat.terrain.mesh.vertices.Count, "Flat vertices converted to list count");
            AssertEqual(6, manifestFlat.terrain.mesh.indices.Count, "Flat indices count");
            AssertApproxEqual(1000.0f, manifestFlat.terrain.mesh.vertices[1][0], 0.01f, "Flat vertex [1].x");
        }

        private static void TestTemplatedZone_SubDistrictHierarchyAndZoneMetadata()
        {
            string templatedJson = @"{
                ""zones"": [
                    {
                        ""id"": ""zone_military_base"",
                        ""name"": ""Fortified Base Bravo"",
                        ""zone_type"": ""military_base"",
                        ""faction"": ""B"",
                        ""destruction"": ""03"",
                        ""center"": [300.0, 20.0, 400.0],
                        ""radius"": 90.0,
                        ""density"": 0.75
                    }
                ],
                ""buildings"": [
                    {
                        ""id"": ""bld_hq"",
                        ""zone_id"": ""zone_military_base"",
                        ""prefab_name"": ""SM_Bld_Village_House_01"",
                        ""placement_role"": ""command"",
                        ""district_id"": ""command_core"",
                        ""position"": [300.0, 20.0, 400.0]
                    },
                    {
                        ""id"": ""bld_tent_01"",
                        ""zone_id"": ""zone_military_base"",
                        ""prefab_name"": ""SM_Bld_Tent_01"",
                        ""placement_role"": ""barracks"",
                        ""district_id"": ""barracks_row"",
                        ""position"": [280.0, 20.0, 390.0]
                    },
                    {
                        ""id"": ""bld_tent_02"",
                        ""zone_id"": ""zone_military_base"",
                        ""prefab_name"": ""SM_Bld_Tent_01"",
                        ""placement_role"": ""barracks"",
                        ""district_id"": ""barracks_row"",
                        ""position"": [280.0, 20.0, 410.0]
                    }
                ]
            }";

            WorldManifest manifest = ManifestJsonParser.Parse(templatedJson);
            AssertEqual(1, manifest.zones.Count, "1 zone");
            AssertEqual("military_base", manifest.zones[0].zone_type, "Zone type parsed");
            AssertEqual("command_core", manifest.buildings[0].district_id, "District id parsed");

            // Build hierarchy using Editor Window simulation
            var root = new GameObject("[WorldGen_Output]");
            var zonesRoot = new GameObject("Zones");
            zonesRoot.transform.SetParent(root.transform);

            var z = manifest.zones[0];
            string zName = $"Zone_{z.id}_Faction{z.GetNormalizedFaction()}_Destruction{z.GetNormalizedDestruction()}";
            GameObject zGO = new GameObject(zName);
            zGO.transform.SetParent(zonesRoot.transform, false);

            ZoneMetadata meta = zGO.AddComponent<ZoneMetadata>();
            meta.zoneId = z.id;
            meta.zoneName = z.name;
            meta.zoneType = z.zone_type;
            meta.faction = z.GetNormalizedFaction();
            meta.destruction = z.GetNormalizedDestruction();
            meta.density = z.density;
            meta.radius = z.radius;
            meta.center = z.GetCenterVector();

            AssertEqual("military_base", meta.zoneType, "ZoneMetadata type");
            AssertApproxEqual(0.75f, meta.density, 0.01f, "ZoneMetadata density");
            AssertApproxEqual(90.0f, meta.radius, 0.01f, "ZoneMetadata radius");

            // Spawn buildings with district containers
            var districtTransforms = new Dictionary<string, Transform>();
            foreach (var b in manifest.buildings)
            {
                string districtName = $"District_{b.district_id}";
                if (!districtTransforms.TryGetValue(districtName, out Transform dTrans))
                {
                    GameObject dGO = new GameObject(districtName);
                    dGO.transform.SetParent(zGO.transform, false);
                    dTrans = dGO.transform;
                    districtTransforms[districtName] = dTrans;
                }

                GameObject bGO = PrefabSpawner.SpawnBuilding(b, z, dTrans, "Assets/PolygonMilitary/Prefabs");
                Assert(bGO != null, $"Building {b.id} spawned");
            }

            // Validate sub-district structure
            AssertEqual(2, zGO.transform.childCount, "Zone has 2 sub-districts (District_command_core, District_barracks_row)");
            AssertEqual("District_command_core", zGO.transform.GetChild(0).gameObject.name, "First sub-district name");
            AssertEqual(1, zGO.transform.GetChild(0).childCount, "District_command_core has 1 building (HQ)");
            AssertEqual("District_barracks_row", zGO.transform.GetChild(1).gameObject.name, "Second sub-district name");
            AssertEqual(2, zGO.transform.GetChild(1).childCount, "District_barracks_row has 2 tents");
        }

        private static void TestTerrainMode_DualModeExecution()
        {
            var manifest = new TerrainManifest
            {
                resolution = 65,
                width = 1000f,
                height_scale = 150f,
                length = 1000f,
                raw_heightmap_2d = new float[,] { { 0f, 50f }, { 50f, 100f } },
                mesh = new MeshDataManifest
                {
                    vertices = new List<float[]>
                    {
                        new float[] { 0f, 0f, 0f },
                        new float[] { 1000f, 0f, 0f },
                        new float[] { 0f, 0f, 1000f }
                    },
                    indices = new List<int> { 0, 1, 2 }
                }
            };

            // Test Mode 1: AdaptiveDecimatedMesh
            var root1 = new GameObject("Root1");
            GameObject adaptiveGO = AdaptiveMeshGenerator.BuildAdaptiveMesh(manifest, root1.transform);
            Assert(adaptiveGO != null, "AdaptiveMesh built in AdaptiveDecimatedMesh mode");
            AssertEqual(1, root1.transform.childCount, "Only AdaptiveTerrainMesh created");

            // Test Mode 2: StandardTerrain
            var root2 = new GameObject("Root2");
            Terrain standardTerrain;
            GameObject standardGO = TerrainGenerator.BuildTerrain(manifest, root2.transform, out standardTerrain);
            Assert(standardGO != null, "Standard Terrain built in StandardTerrain mode");
            Assert(standardTerrain != null, "Terrain component created");

            // Test Mode 3: HybridBoth
            var root3 = new GameObject("Root3");
            GameObject adGO = AdaptiveMeshGenerator.BuildAdaptiveMesh(manifest, root3.transform);
            Terrain stTerrain;
            GameObject stGO = TerrainGenerator.BuildTerrain(manifest, root3.transform, out stTerrain);
            Assert(adGO != null && stGO != null, "Both AdaptiveTerrainMesh and Terrain built in Hybrid mode");
            AssertEqual(2, root3.transform.childCount, "Hybrid root has 2 children");
        }

        private static void TestEndToEnd_AdaptiveMeshSampleImport()
        {
            string samplePath = "/Users/jack/worldgen/unity/sample_world_manifest.json";
            Assert(File.Exists(samplePath), "sample_world_manifest.json must exist");

            string json = File.ReadAllText(samplePath);
            WorldManifest manifest = ManifestJsonParser.Parse(json);
            Assert(manifest != null && manifest.terrain.mesh != null, "Sample manifest contains mesh");

            var root = new GameObject("[WorldGen_Output]");
            var terrainParent = new GameObject("Terrain");
            terrainParent.transform.SetParent(root.transform);

            // Build AdaptiveTerrainMesh
            GameObject adaptiveGO = AdaptiveMeshGenerator.BuildAdaptiveMesh(manifest.terrain, terrainParent.transform);
            Assert(adaptiveGO != null, "AdaptiveTerrainMesh instantiated in sample import");
            MeshFilter mf = adaptiveGO.GetComponent<MeshFilter>();
            Assert(mf != null && mf.sharedMesh != null, "MeshFilter sharedMesh populated");
            AssertEqual(8, mf.sharedMesh.vertices.Length, "Sample mesh vertices count matches 8");
            AssertEqual(18, mf.sharedMesh.triangles.Length, "Sample mesh triangles count matches 18");

            // Build Roads conforming to adaptive mesh
            var roadsParent = new GameObject("Roads");
            roadsParent.transform.SetParent(root.transform);
            foreach (var road in manifest.roads)
            {
                GameObject roadGO = RoadMeshBuilder.BuildRoad(road, roadsParent.transform, null, adaptiveGO, true, true);
                Assert(roadGO != null, "Road successfully created conforming to AdaptiveTerrainMesh");
            }
        }

        #endregion
    }
}

