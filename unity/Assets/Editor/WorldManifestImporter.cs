// ====================================================================================================================
// WorldManifestImporter.cs - Synty PolygonMilitary Procedural World Importer for Unity
//
// Description:
//   Production-grade Unity Editor importer for procedural world manifests (world_manifest.json).
//   Instantiates Unity Terrain with bilinear heightmap interpolation, spawns linked prefabs using
//   PrefabUtility.InstantiatePrefab, dynamically swaps materials and textures for Factions (A, B, C)
//   and Destruction states (01, 02, 03, 04), and constructs conforming 3D road ribbon meshes.
//
// Author: Procedural WorldGen Team
// License: MIT
// ====================================================================================================================

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

#if UNITY_EDITOR
using UnityEditor;
#endif

namespace WorldGen.Core
{
    #region Data Models

    [Serializable]
    public class WorldManifest
    {
        public ManifestMetadata metadata = new ManifestMetadata();
        public TerrainManifest terrain = new TerrainManifest();
        public List<ZoneManifest> zones = new List<ZoneManifest>();
        public List<BuildingManifest> buildings = new List<BuildingManifest>();
        public List<RoadManifest> roads = new List<RoadManifest>();
    }

    [Serializable]
    public class ManifestMetadata
    {
        public int seed = 0;
        public string generator_version = "1.0.0";
        public string generator = "Procedural WorldGen";
        public string created_at = "";
        public string timestamp = "";
        public float[] bounds = new float[6]; // [minX, minY, minZ, maxX, maxY, maxZ]
    }

    [Serializable]
    public class MeshDataManifest
    {
        public List<float[]> vertices = new List<float[]>();
        public List<int> indices = new List<int>();
        public List<float[]> normals = new List<float[]>();
        public List<float[]> uvs = new List<float[]>();
        public float[] flat_vertices = null;
        public int[] flat_indices = null;
        public float[] flat_normals = null;
        public float[] flat_uvs = null;
        public int vertex_count = 0;
        public int triangle_count = 0;
        public float decimation_ratio = 1.0f;
    }

    [Serializable]
    public class TerrainManifest
    {
        public int resolution = 513;
        public float[] world_size = new float[] { 1000f, 150f, 1000f }; // [width, height_scale, length]
        public float width = 1000f;
        public float length = 1000f;
        public float height_scale = 150f;
        public float min_height = 0f;
        public float max_height = 150f;
        public float[,] raw_heightmap_2d = null;
        public float[] raw_heightmap_1d = null;
        public MeshDataManifest mesh = null;

        public float GetWidth() => (world_size != null && world_size.Length >= 3 && world_size[0] > 0) ? world_size[0] : (width > 0 ? width : 1000f);
        public float GetHeightScale() => (world_size != null && world_size.Length >= 3 && world_size[1] > 0) ? world_size[1] : (height_scale > 0 ? height_scale : 150f);
        public float GetLength() => (world_size != null && world_size.Length >= 3 && world_size[2] > 0) ? world_size[2] : (length > 0 ? length : 1000f);
    }

    [Serializable]
    public class ZoneManifest
    {
        public string id = "";
        public string name = "";
        public string zone_type = "military_base";
        public string faction = "A"; // "A", "B", "C"
        public string destruction = "01"; // "01", "02", "03", "04"
        public float[] center = new float[] { 0f, 0f, 0f };
        public float radius = 50f;
        public float density = 0.5f;
        public float building_density = 0.5f;
        public List<float[]> footprint_points = new List<float[]>();
        public List<string> building_ids = new List<string>();

        public Vector3 GetCenterVector()
        {
            if (center != null && center.Length >= 3)
                return new Vector3(center[0], center[1], center[2]);
            return Vector3.zero;
        }

        public string GetNormalizedFaction()
        {
            if (string.IsNullOrEmpty(faction)) return "A";
            string f = faction.Trim().ToUpperInvariant();
            if (f == "A" || f == "B" || f == "C") return f;
            if (f.EndsWith("A")) return "A";
            if (f.EndsWith("B")) return "B";
            if (f.EndsWith("C")) return "C";
            return "A";
        }

        public string GetNormalizedDestruction()
        {
            if (string.IsNullOrEmpty(destruction)) return "01";
            string d = destruction.Trim();
            if (d == "01" || d == "02" || d == "03" || d == "04") return d;
            if (d == "1") return "01";
            if (d == "2") return "02";
            if (d == "3") return "03";
            if (d == "4") return "04";
            return "01";
        }
    }

    [Serializable]
    public class ZoneMetadata : MonoBehaviour
    {
        public string zoneId = "";
        public string zoneName = "";
        public string zoneType = "military_base";
        public string faction = "A";
        public string destruction = "01";
        public float density = 0.5f;
        public float radius = 50f;
        public Vector3 center = Vector3.zero;
    }

    [Serializable]
    public class BuildingManifest
    {
        public string id = "";
        public string zone_id = "";
        public string prefab_name = "";
        public string placement_role = "";
        public string district_id = "";
        public string sub_district = "";
        public float[] position = new float[] { 0f, 0f, 0f };
        public float[] rotation = new float[] { 0f, 0f, 0f }; // Euler [x,y,z] or Quaternion [x,y,z,w]
        public float[] scale = new float[] { 1f, 1f, 1f };
        public BoundingBoxManifest bounding_box = null;
        public BoundingBoxManifest bbox = null;
        public string faction = "";
        public string destruction = "";

        public Vector3 GetPosition()
        {
            if (position != null && position.Length >= 3)
                return new Vector3(position[0], position[1], position[2]);
            return Vector3.zero;
        }

        public Quaternion GetRotation()
        {
            if (rotation == null || rotation.Length == 0)
                return Quaternion.identity;
            if (rotation.Length == 4)
            {
                // Validate quaternion magnitude
                float magSq = rotation[0] * rotation[0] + rotation[1] * rotation[1] + rotation[2] * rotation[2] + rotation[3] * rotation[3];
                if (magSq > 0.001f)
                    return new Quaternion(rotation[0], rotation[1], rotation[2], rotation[3]);
                return Quaternion.identity;
            }
            if (rotation.Length == 3)
                return Quaternion.Euler(rotation[0], rotation[1], rotation[2]);
            return Quaternion.identity;
        }

        public Vector3 GetScale()
        {
            if (scale != null && scale.Length >= 3)
                return new Vector3(scale[0], scale[1], scale[2]);
            return Vector3.one;
        }

        public BoundingBoxManifest GetBoundingBox()
        {
            if (bounding_box != null)
                return bounding_box;
            if (bbox != null)
                return bbox;
            return new BoundingBoxManifest();
        }
    }

    [Serializable]
    public class BoundingBoxManifest
    {
        public float[] min = new float[] { -0.5f, 0f, -0.5f };
        public float[] max = new float[] { 0.5f, 1f, 0.5f };
        public float[] size = new float[] { 1f, 1f, 1f };
        public float[] center = new float[] { 0f, 0.5f, 0f };

        public Vector3 GetSize()
        {
            if (size != null && size.Length >= 3)
                return new Vector3(size[0], size[1], size[2]);
            if (min != null && max != null && min.Length >= 3 && max.Length >= 3)
                return new Vector3(Mathf.Abs(max[0] - min[0]), Mathf.Abs(max[1] - min[1]), Mathf.Abs(max[2] - min[2]));
            return Vector3.one;
        }

        public Vector3 GetCenter()
        {
            if (center != null && center.Length >= 3)
                return new Vector3(center[0], center[1], center[2]);
            if (min != null && max != null && min.Length >= 3 && max.Length >= 3)
                return new Vector3((min[0] + max[0]) * 0.5f, (min[1] + max[1]) * 0.5f, (min[2] + max[2]) * 0.5f);
            return new Vector3(0f, 0.5f, 0f);
        }
    }

    [Serializable]
    public class RoadManifest
    {
        public string id = "";
        public string from_zone = "";
        public string to_zone = "";
        public string source_zone = "";
        public string target_zone = "";
        public float width = 6f;
        public string surface_type = "asphalt";
        public List<float[]> waypoints = new List<float[]>();

        public string GetFromZone() => !string.IsNullOrEmpty(from_zone) ? from_zone : source_zone;
        public string GetToZone() => !string.IsNullOrEmpty(to_zone) ? to_zone : target_zone;
    }

    #endregion

    #region Robust JSON Deserializer

    /// <summary>
    /// Lightweight, high-performance, resilient JSON parser capable of parsing nested structures,
    /// 2D float arrays, mixed types, and mapping directly to WorldManifest without external dependencies.
    /// </summary>
    public static class ManifestJsonParser
    {
        public static WorldManifest Parse(string json)
        {
            if (string.IsNullOrEmpty(json))
                throw new ArgumentException("Input JSON string is null or empty.");

            int index = 0;
            object root = ParseValue(json, ref index);
            if (!(root is Dictionary<string, object> rootDict))
                throw new FormatException("Root of JSON must be an object.");

            var manifest = new WorldManifest();

            // 1. Metadata
            if (rootDict.TryGetValue("metadata", out object metaObj) && metaObj is Dictionary<string, object> metaDict)
            {
                if (metaDict.TryGetValue("seed", out object seedVal)) manifest.metadata.seed = ConvertToInt(seedVal);
                if (metaDict.TryGetValue("generator_version", out object gvVal)) manifest.metadata.generator_version = gvVal?.ToString() ?? "";
                if (metaDict.TryGetValue("generator", out object gVal)) manifest.metadata.generator = gVal?.ToString() ?? "";
                if (metaDict.TryGetValue("created_at", out object caVal)) manifest.metadata.created_at = caVal?.ToString() ?? "";
                if (metaDict.TryGetValue("timestamp", out object tsVal)) manifest.metadata.timestamp = tsVal?.ToString() ?? "";
                if (metaDict.TryGetValue("bounds", out object bVal) && bVal is List<object> bList)
                    manifest.metadata.bounds = ConvertToFloatArray(bList);
            }

            // 2. Terrain
            if (rootDict.TryGetValue("terrain", out object terrainObj) && terrainObj is Dictionary<string, object> tDict)
            {
                if (tDict.TryGetValue("resolution", out object resVal)) manifest.terrain.resolution = ConvertToInt(resVal);
                if (tDict.TryGetValue("width", out object wVal)) manifest.terrain.width = ConvertToFloat(wVal);
                if (tDict.TryGetValue("length", out object lVal)) manifest.terrain.length = ConvertToFloat(lVal);
                if (tDict.TryGetValue("height_scale", out object hsVal)) manifest.terrain.height_scale = ConvertToFloat(hsVal);
                if (tDict.TryGetValue("min_height", out object minhVal)) manifest.terrain.min_height = ConvertToFloat(minhVal);
                if (tDict.TryGetValue("max_height", out object maxhVal)) manifest.terrain.max_height = ConvertToFloat(maxhVal);
                if (tDict.TryGetValue("world_size", out object wsVal) && wsVal is List<object> wsList)
                    manifest.terrain.world_size = ConvertToFloatArray(wsList);

                // Check terrain mesh (Adaptive Decimated Mesh)
                if (tDict.TryGetValue("mesh", out object meshObj) && meshObj is Dictionary<string, object> mDict)
                {
                    manifest.terrain.mesh = ParseMeshData(mDict);
                }

                // Check heightmap (2D or 1D)
                if (tDict.TryGetValue("heightmap", out object hmObj))
                {
                    if (hmObj is List<object> hmList)
                    {
                        if (hmList.Count > 0 && hmList[0] is List<object>)
                        {
                            // 2D heightmap
                            int rows = hmList.Count;
                            int cols = ((List<object>)hmList[0]).Count;
                            float[,] hm2d = new float[rows, cols];
                            for (int r = 0; r < rows; r++)
                            {
                                var rowList = (List<object>)hmList[r];
                                for (int c = 0; c < Math.Min(cols, rowList.Count); c++)
                                {
                                    hm2d[r, c] = ConvertToFloat(rowList[c]);
                                }
                            }
                            manifest.terrain.raw_heightmap_2d = hm2d;
                            if (manifest.terrain.resolution <= 0) manifest.terrain.resolution = cols;
                        }
                        else
                        {
                            // 1D heightmap
                            manifest.terrain.raw_heightmap_1d = ConvertToFloatArray(hmList);
                            if (manifest.terrain.resolution <= 0)
                                manifest.terrain.resolution = Mathf.RoundToInt(Mathf.Sqrt(manifest.terrain.raw_heightmap_1d.Length));
                        }
                    }
                }
                else if (tDict.TryGetValue("heights", out object hObj) && hObj is List<object> hList)
                {
                    manifest.terrain.raw_heightmap_1d = ConvertToFloatArray(hList);
                }
            }

            // 3. Zones
            if (rootDict.TryGetValue("zones", out object zonesObj) && zonesObj is List<object> zonesList)
            {
                foreach (var zItem in zonesList)
                {
                    if (!(zItem is Dictionary<string, object> zDict)) continue;
                    var z = new ZoneManifest();
                    if (zDict.TryGetValue("id", out object idVal)) z.id = idVal?.ToString() ?? "";
                    if (zDict.TryGetValue("name", out object nameVal)) z.name = nameVal?.ToString() ?? "";
                    if (zDict.TryGetValue("zone_type", out object ztVal)) z.zone_type = ztVal?.ToString() ?? "military_base";
                    else if (zDict.TryGetValue("type", out object ztVal2)) z.zone_type = ztVal2?.ToString() ?? "military_base";
                    if (zDict.TryGetValue("faction", out object fVal)) z.faction = fVal?.ToString() ?? "A";
                    if (zDict.TryGetValue("destruction", out object dVal)) z.destruction = dVal?.ToString() ?? "01";
                    if (zDict.TryGetValue("radius", out object radVal)) z.radius = ConvertToFloat(radVal);
                    if (zDict.TryGetValue("density", out object denVal)) z.density = ConvertToFloat(denVal);
                    if (zDict.TryGetValue("building_density", out object bdenVal)) z.building_density = ConvertToFloat(bdenVal);
                    if (zDict.TryGetValue("center", out object cVal) && cVal is List<object> cList)
                        z.center = ConvertToFloatArray(cList);
                    if (zDict.TryGetValue("footprint_points", out object fpVal) && fpVal is List<object> fpList)
                    {
                        foreach (var fpItem in fpList)
                        {
                            if (fpItem is List<object> ptList)
                                z.footprint_points.Add(ConvertToFloatArray(ptList));
                        }
                    }
                    if (zDict.TryGetValue("building_ids", out object bidsVal) && bidsVal is List<object> bidsList)
                    {
                        foreach (var bid in bidsList)
                            z.building_ids.Add(bid?.ToString() ?? "");
                    }
                    manifest.zones.Add(z);
                }
            }

            // 4. Buildings
            if (rootDict.TryGetValue("buildings", out object bldsObj) && bldsObj is List<object> bldsList)
            {
                foreach (var bItem in bldsList)
                {
                    if (!(bItem is Dictionary<string, object> bDict)) continue;
                    var b = new BuildingManifest();
                    if (bDict.TryGetValue("id", out object idVal)) b.id = idVal?.ToString() ?? "";
                    if (bDict.TryGetValue("zone_id", out object zidVal)) b.zone_id = zidVal?.ToString() ?? "";
                    if (bDict.TryGetValue("prefab_name", out object pnameVal)) b.prefab_name = pnameVal?.ToString() ?? "";
                    if (bDict.TryGetValue("placement_role", out object prVal)) b.placement_role = prVal?.ToString() ?? "";
                    if (bDict.TryGetValue("district_id", out object didVal)) b.district_id = didVal?.ToString() ?? "";
                    if (bDict.TryGetValue("sub_district", out object sdidVal)) b.sub_district = sdidVal?.ToString() ?? "";
                    if (bDict.TryGetValue("faction", out object fVal)) b.faction = fVal?.ToString() ?? "";
                    if (bDict.TryGetValue("destruction", out object dVal)) b.destruction = dVal?.ToString() ?? "";
                    if (bDict.TryGetValue("position", out object posVal) && posVal is List<object> posList)
                        b.position = ConvertToFloatArray(posList);
                    if (bDict.TryGetValue("rotation", out object rotVal) && rotVal is List<object> rotList)
                        b.rotation = ConvertToFloatArray(rotList);
                    if (bDict.TryGetValue("scale", out object sVal) && sVal is List<object> sList)
                        b.scale = ConvertToFloatArray(sList);

                    // Bounding box
                    if (bDict.TryGetValue("bounding_box", out object bboxObj) && bboxObj is Dictionary<string, object> bboxDict)
                    {
                        b.bounding_box = ParseBoundingBox(bboxDict);
                        b.bbox = b.bounding_box;
                    }
                    else if (bDict.TryGetValue("bbox", out object bboxObj2) && bboxObj2 is Dictionary<string, object> bboxDict2)
                    {
                        b.bbox = ParseBoundingBox(bboxDict2);
                        b.bounding_box = b.bbox;
                    }

                    manifest.buildings.Add(b);
                }
            }

            // 5. Roads
            if (rootDict.TryGetValue("roads", out object roadsObj) && roadsObj is List<object> roadsList)
            {
                foreach (var rItem in roadsList)
                {
                    if (!(rItem is Dictionary<string, object> rDict)) continue;
                    var r = new RoadManifest();
                    if (rDict.TryGetValue("id", out object idVal)) r.id = idVal?.ToString() ?? "";
                    if (rDict.TryGetValue("from_zone", out object fzVal)) r.from_zone = fzVal?.ToString() ?? "";
                    if (rDict.TryGetValue("to_zone", out object tzVal)) r.to_zone = tzVal?.ToString() ?? "";
                    if (rDict.TryGetValue("source_zone", out object szVal)) r.source_zone = szVal?.ToString() ?? "";
                    if (rDict.TryGetValue("target_zone", out object tgzVal)) r.target_zone = tgzVal?.ToString() ?? "";
                    if (rDict.TryGetValue("width", out object wVal)) r.width = ConvertToFloat(wVal);
                    if (rDict.TryGetValue("surface_type", out object stVal)) r.surface_type = stVal?.ToString() ?? "asphalt";
                    if (rDict.TryGetValue("waypoints", out object wpVal) && wpVal is List<object> wpList)
                    {
                        foreach (var wpItem in wpList)
                        {
                            if (wpItem is List<object> ptList)
                                r.waypoints.Add(ConvertToFloatArray(ptList));
                        }
                    }
                    manifest.roads.Add(r);
                }
            }

            return manifest;
        }

        private static MeshDataManifest ParseMeshData(Dictionary<string, object> mDict)
        {
            var mesh = new MeshDataManifest();
            if (mDict.TryGetValue("vertex_count", out object vcVal)) mesh.vertex_count = ConvertToInt(vcVal);
            if (mDict.TryGetValue("triangle_count", out object tcVal)) mesh.triangle_count = ConvertToInt(tcVal);
            if (mDict.TryGetValue("decimation_ratio", out object drVal)) mesh.decimation_ratio = ConvertToFloat(drVal);

            // Vertices (support nested [[x,y,z], ...] and flat [x0, y0, z0, ...])
            if (mDict.TryGetValue("vertices", out object vertsObj) && vertsObj is List<object> vertsList)
            {
                if (vertsList.Count > 0 && vertsList[0] is List<object>)
                {
                    foreach (var vItem in vertsList)
                    {
                        if (vItem is List<object> vList)
                            mesh.vertices.Add(ConvertToFloatArray(vList));
                    }
                }
                else if (vertsList.Count > 0)
                {
                    mesh.flat_vertices = ConvertToFloatArray(vertsList);
                    for (int i = 0; i + 2 < mesh.flat_vertices.Length; i += 3)
                    {
                        mesh.vertices.Add(new float[] { mesh.flat_vertices[i], mesh.flat_vertices[i + 1], mesh.flat_vertices[i + 2] });
                    }
                }
            }

            // Indices / Triangles (support nested/flat)
            List<object> indicesList = null;
            if (mDict.TryGetValue("indices", out object idxObj) && idxObj is List<object> iList)
                indicesList = iList;
            else if (mDict.TryGetValue("triangles", out object triObj) && triObj is List<object> tList)
                indicesList = tList;

            if (indicesList != null)
            {
                mesh.flat_indices = new int[indicesList.Count];
                for (int i = 0; i < indicesList.Count; i++)
                {
                    int val = ConvertToInt(indicesList[i]);
                    mesh.indices.Add(val);
                    mesh.flat_indices[i] = val;
                }
            }

            // Normals (support nested [[x,y,z], ...] and flat [x0, y0, z0, ...])
            if (mDict.TryGetValue("normals", out object normsObj) && normsObj is List<object> normsList)
            {
                if (normsList.Count > 0 && normsList[0] is List<object>)
                {
                    foreach (var nItem in normsList)
                    {
                        if (nItem is List<object> nList)
                            mesh.normals.Add(ConvertToFloatArray(nList));
                    }
                }
                else if (normsList.Count > 0)
                {
                    mesh.flat_normals = ConvertToFloatArray(normsList);
                    for (int i = 0; i + 2 < mesh.flat_normals.Length; i += 3)
                    {
                        mesh.normals.Add(new float[] { mesh.flat_normals[i], mesh.flat_normals[i + 1], mesh.flat_normals[i + 2] });
                    }
                }
            }

            // UVs (support nested [[u,v], ...] and flat [u0, v0, ...])
            if (mDict.TryGetValue("uvs", out object uvsObj) && uvsObj is List<object> uvsList)
            {
                if (uvsList.Count > 0 && uvsList[0] is List<object>)
                {
                    foreach (var uvItem in uvsList)
                    {
                        if (uvItem is List<object> uvList)
                            mesh.uvs.Add(ConvertToFloatArray(uvList));
                    }
                }
                else if (uvsList.Count > 0)
                {
                    mesh.flat_uvs = ConvertToFloatArray(uvsList);
                    for (int i = 0; i + 1 < mesh.flat_uvs.Length; i += 2)
                    {
                        mesh.uvs.Add(new float[] { mesh.flat_uvs[i], mesh.flat_uvs[i + 1] });
                    }
                }
            }

            if (mesh.vertex_count <= 0)
                mesh.vertex_count = mesh.vertices.Count;
            if (mesh.triangle_count <= 0)
                mesh.triangle_count = mesh.indices.Count / 3;

            return mesh;
        }

        private static BoundingBoxManifest ParseBoundingBox(Dictionary<string, object> dict)
        {
            var bbox = new BoundingBoxManifest();
            if (dict.TryGetValue("min", out object minVal) && minVal is List<object> minList)
                bbox.min = ConvertToFloatArray(minList);
            if (dict.TryGetValue("max", out object maxVal) && maxVal is List<object> maxList)
                bbox.max = ConvertToFloatArray(maxList);
            if (dict.TryGetValue("size", out object sizeVal) && sizeVal is List<object> sizeList)
                bbox.size = ConvertToFloatArray(sizeList);
            if (dict.TryGetValue("center", out object cVal) && cVal is List<object> cList)
                bbox.center = ConvertToFloatArray(cList);
            return bbox;
        }

        private static float[] ConvertToFloatArray(List<object> list)
        {
            float[] result = new float[list.Count];
            for (int i = 0; i < list.Count; i++)
                result[i] = ConvertToFloat(list[i]);
            return result;
        }

        private static float ConvertToFloat(object obj)
        {
            if (obj == null) return 0f;
            if (obj is float f) return f;
            if (obj is double d) return (float)d;
            if (obj is int i) return (float)i;
            if (obj is long l) return (float)l;
            if (float.TryParse(obj.ToString(), NumberStyles.Any, CultureInfo.InvariantCulture, out float parsed))
                return parsed;
            return 0f;
        }

        private static int ConvertToInt(object obj)
        {
            if (obj == null) return 0;
            if (obj is int i) return i;
            if (obj is long l) return (int)l;
            if (obj is float f) return Mathf.RoundToInt(f);
            if (obj is double d) return (int)Math.Round(d);
            if (int.TryParse(obj.ToString(), NumberStyles.Any, CultureInfo.InvariantCulture, out int parsed))
                return parsed;
            return 0;
        }

        #region Tokenizer & Recursive Descent Parser

        private static object ParseValue(string json, ref int index)
        {
            SkipWhitespace(json, ref index);
            if (index >= json.Length) return null;

            char c = json[index];
            if (c == '{') return ParseObject(json, ref index);
            if (c == '[') return ParseArray(json, ref index);
            if (c == '"') return ParseString(json, ref index);
            if (c == 't' || c == 'f') return ParseBool(json, ref index);
            if (c == 'n') return ParseNull(json, ref index);
            if (c == '-' || (c >= '0' && c <= '9')) return ParseNumber(json, ref index);

            throw new FormatException($"Unexpected character '{c}' at position {index}.");
        }

        private static Dictionary<string, object> ParseObject(string json, ref int index)
        {
            var dict = new Dictionary<string, object>(StringComparer.OrdinalIgnoreCase);
            index++; // skip '{'

            while (index < json.Length)
            {
                SkipWhitespace(json, ref index);
                if (index >= json.Length) break;
                if (json[index] == '}')
                {
                    index++;
                    return dict;
                }

                if (json[index] != '"')
                    throw new FormatException($"Expected string key in object at position {index}.");

                string key = ParseString(json, ref index);
                SkipWhitespace(json, ref index);

                if (index >= json.Length || json[index] != ':')
                    throw new FormatException($"Expected ':' after key '{key}' at position {index}.");
                index++; // skip ':'

                object val = ParseValue(json, ref index);
                dict[key] = val;

                SkipWhitespace(json, ref index);
                if (index < json.Length && json[index] == ',')
                {
                    index++;
                    continue;
                }
                if (index < json.Length && json[index] == '}')
                {
                    index++;
                    return dict;
                }
            }

            throw new FormatException("Unclosed object in JSON.");
        }

        private static List<object> ParseArray(string json, ref int index)
        {
            var list = new List<object>();
            index++; // skip '['

            while (index < json.Length)
            {
                SkipWhitespace(json, ref index);
                if (index >= json.Length) break;
                if (json[index] == ']')
                {
                    index++;
                    return list;
                }

                object val = ParseValue(json, ref index);
                list.Add(val);

                SkipWhitespace(json, ref index);
                if (index < json.Length && json[index] == ',')
                {
                    index++;
                    continue;
                }
                if (index < json.Length && json[index] == ']')
                {
                    index++;
                    return list;
                }
            }

            throw new FormatException("Unclosed array in JSON.");
        }

        private static string ParseString(string json, ref int index)
        {
            index++; // skip opening '"'
            var sb = new StringBuilder();
            while (index < json.Length)
            {
                char c = json[index++];
                if (c == '"') return sb.ToString();
                if (c == '\\')
                {
                    if (index >= json.Length) break;
                    char esc = json[index++];
                    switch (esc)
                    {
                        case '"': sb.Append('"'); break;
                        case '\\': sb.Append('\\'); break;
                        case '/': sb.Append('/'); break;
                        case 'b': sb.Append('\b'); break;
                        case 'f': sb.Append('\f'); break;
                        case 'n': sb.Append('\n'); break;
                        case 'r': sb.Append('\r'); break;
                        case 't': sb.Append('\t'); break;
                        case 'u':
                            if (index + 4 <= json.Length)
                            {
                                string hex = json.Substring(index, 4);
                                index += 4;
                                sb.Append((char)Convert.ToInt32(hex, 16));
                            }
                            break;
                        default: sb.Append(esc); break;
                    }
                }
                else
                {
                    sb.Append(c);
                }
            }
            throw new FormatException("Unterminated string in JSON.");
        }

        private static object ParseNumber(string json, ref int index)
        {
            int start = index;
            if (json[index] == '-') index++;
            while (index < json.Length && (char.IsDigit(json[index]) || json[index] == '.' || json[index] == 'e' || json[index] == 'E' || json[index] == '+' || json[index] == '-'))
            {
                if ((json[index] == '+' || json[index] == '-') && json[index - 1] != 'e' && json[index - 1] != 'E')
                    break;
                index++;
            }

            string numStr = json.Substring(start, index - start);
            if (numStr.Contains(".") || numStr.Contains("e") || numStr.Contains("E"))
            {
                if (double.TryParse(numStr, NumberStyles.Any, CultureInfo.InvariantCulture, out double dVal))
                    return dVal;
            }
            else
            {
                if (long.TryParse(numStr, NumberStyles.Any, CultureInfo.InvariantCulture, out long lVal))
                {
                    if (lVal >= int.MinValue && lVal <= int.MaxValue) return (int)lVal;
                    return lVal;
                }
            }

            return 0f;
        }

        private static bool ParseBool(string json, ref int index)
        {
            if (index + 4 <= json.Length && json.Substring(index, 4) == "true")
            {
                index += 4;
                return true;
            }
            if (index + 5 <= json.Length && json.Substring(index, 5) == "false")
            {
                index += 5;
                return false;
            }
            throw new FormatException($"Invalid boolean at position {index}.");
        }

        private static object ParseNull(string json, ref int index)
        {
            if (index + 4 <= json.Length && json.Substring(index, 4) == "null")
            {
                index += 4;
                return null;
            }
            throw new FormatException($"Invalid null at position {index}.");
        }

        private static void SkipWhitespace(string json, ref int index)
        {
            while (index < json.Length)
            {
                char c = json[index];
                if (c == ' ' || c == '\t' || c == '\n' || c == '\r')
                    index++;
                else
                    break;
            }
        }

        #endregion
    }

    #endregion
}

namespace WorldGen.Editor
{
    using WorldGen.Core;

    #region Terrain Generator

    /// <summary>
    /// Handles procedural TerrainData instantiation, bilinear heightmap resampling,
    /// height normalization, and Unity Terrain GameObject creation.
    /// </summary>
    public static class TerrainGenerator
    {
        public static GameObject BuildTerrain(TerrainManifest manifest, Transform parentTransform, out Terrain outTerrain)
        {
            if (manifest == null)
                throw new ArgumentNullException(nameof(manifest));

            // 1. Determine optimal Unity heightmap resolution (2^n + 1)
            int requestedRes = manifest.resolution > 0 ? manifest.resolution : 513;
            int unityRes = CalculateUnityHeightmapResolution(requestedRes);

            float width = manifest.GetWidth();
            float heightScale = manifest.GetHeightScale();
            float length = manifest.GetLength();

            Debug.Log($"[WorldGen] Building Terrain: Size=({width}x{heightScale}x{length}), HeightmapResolution={unityRes} (Manifest={requestedRes})");

            // 2. Sample and bilinearly resample heightmap into normalized float[z, x]
            float[,] heights = ResampleHeightmap(manifest, unityRes, heightScale);

            // 3. Create TerrainData
            TerrainData terrainData = new TerrainData();
            terrainData.heightmapResolution = unityRes;
            terrainData.size = new Vector3(width, heightScale, length);
            terrainData.SetHeights(0, 0, heights);

            // 4. Create Terrain GameObject
            GameObject terrainGO = Terrain.CreateTerrainGameObject(terrainData);
            terrainGO.name = "Terrain";
            terrainGO.transform.position = Vector3.zero;
            terrainGO.transform.rotation = Quaternion.identity;
            terrainGO.transform.localScale = Vector3.one;

            if (parentTransform != null)
                terrainGO.transform.SetParent(parentTransform, false);

            outTerrain = terrainGO.GetComponent<Terrain>();

            // Ensure TerrainCollider is configured
            TerrainCollider collider = terrainGO.GetComponent<TerrainCollider>();
            if (collider != null)
                collider.terrainData = terrainData;

#if UNITY_EDITOR
            Undo.RegisterCreatedObjectUndo(terrainGO, "Create WorldGen Terrain");
#endif

            return terrainGO;
        }

        public static int CalculateUnityHeightmapResolution(int inputRes)
        {
            // Unity requires heightmap resolution to be 2^n + 1 (e.g. 65, 129, 257, 513, 1025, 2049, 4097)
            if (inputRes <= 65) return 65;
            if (inputRes <= 129) return 129;
            if (inputRes <= 257) return 257;
            if (inputRes <= 513) return 513;
            if (inputRes <= 1025) return 1025;
            if (inputRes <= 2049) return 2049;
            return 4097;
        }

        public static float[,] ResampleHeightmap(TerrainManifest manifest, int targetResolution, float heightScale)
        {
            float[,] resampled = new float[targetResolution, targetResolution];

            int srcRows = 0;
            int srcCols = 0;

            if (manifest.raw_heightmap_2d != null)
            {
                srcRows = manifest.raw_heightmap_2d.GetLength(0);
                srcCols = manifest.raw_heightmap_2d.GetLength(1);
            }
            else if (manifest.raw_heightmap_1d != null && manifest.raw_heightmap_1d.Length > 0)
            {
                int side = Mathf.RoundToInt(Mathf.Sqrt(manifest.raw_heightmap_1d.Length));
                srcRows = side;
                srcCols = side;
            }

            if (srcRows == 0 || srcCols == 0)
            {
                Debug.LogWarning("[WorldGen] No heightmap data provided in manifest. Generating default flat terrain.");
                return resampled;
            }

            float invScale = heightScale > 1e-4f ? 1f / heightScale : 1f;

            for (int z = 0; z < targetResolution; z++)
            {
                float v = (float)z / (targetResolution - 1); // [0, 1] along Z
                float srcV = v * (srcRows - 1);
                int z0 = Mathf.Clamp(Mathf.FloorToInt(srcV), 0, srcRows - 1);
                int z1 = Mathf.Clamp(z0 + 1, 0, srcRows - 1);
                float fz = srcV - z0;

                for (int x = 0; x < targetResolution; x++)
                {
                    float u = (float)x / (targetResolution - 1); // [0, 1] along X
                    float srcU = u * (srcCols - 1);
                    int x0 = Mathf.Clamp(Mathf.FloorToInt(srcU), 0, srcCols - 1);
                    int x1 = Mathf.Clamp(x0 + 1, 0, srcCols - 1);
                    float fx = srcU - x0;

                    // Fetch 4 corner values
                    float h00 = GetRawHeight(manifest, z0, x0, srcRows, srcCols);
                    float h10 = GetRawHeight(manifest, z0, x1, srcRows, srcCols);
                    float h01 = GetRawHeight(manifest, z1, x0, srcRows, srcCols);
                    float h11 = GetRawHeight(manifest, z1, x1, srcRows, srcCols);

                    // Bilinear interpolation
                    float hTop = Mathf.Lerp(h00, h10, fx);
                    float hBottom = Mathf.Lerp(h01, h11, fx);
                    float hInterp = Mathf.Lerp(hTop, hBottom, fz);

                    // Normalize to [0.0, 1.0] strictly
                    float normalizedHeight = (hInterp > 1.0f) ? Mathf.Clamp01(hInterp * invScale) : Mathf.Clamp01(hInterp);

                    // Unity TerrainData.SetHeights expects [z, x]
                    resampled[z, x] = normalizedHeight;
                }
            }

            return resampled;
        }

        private static float GetRawHeight(TerrainManifest manifest, int z, int x, int rows, int cols)
        {
            if (manifest.raw_heightmap_2d != null)
                return manifest.raw_heightmap_2d[z, x];

            if (manifest.raw_heightmap_1d != null)
            {
                int index = z * cols + x;
                if (index >= 0 && index < manifest.raw_heightmap_1d.Length)
                    return manifest.raw_heightmap_1d[index];
            }

            return 0f;
        }
    }

    #endregion

    #region Adaptive Decimated Mesh Generator

    /// <summary>
    /// Constructs optimized AdaptiveTerrainMesh GameObjects from decimated mesh data (vertices, indices, normals, UVs)
    /// supporting 32-bit index buffers (IndexFormat.UInt32) when vertex count > 65,535.
    /// </summary>
    public static class AdaptiveMeshGenerator
    {
        public static GameObject BuildAdaptiveMesh(TerrainManifest manifest, Transform parentTransform)
        {
            if (manifest == null || manifest.mesh == null)
                return null;

            var meshData = manifest.mesh;
            int vertCount = meshData.vertices != null && meshData.vertices.Count > 0
                ? meshData.vertices.Count
                : (meshData.flat_vertices != null ? meshData.flat_vertices.Length / 3 : 0);

            if (vertCount == 0)
                return null;

            Mesh mesh = new Mesh();
            mesh.name = "Terrain_AdaptiveDecimatedMesh";

            // 32-bit index format configuration if vertex count exceeds 65,535
            if (vertCount > 65535)
            {
                mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
            }

            Vector3[] vertices = new Vector3[vertCount];
            Vector2[] uvs = new Vector2[vertCount];
            float width = manifest.GetWidth();
            float length = manifest.GetLength();

            for (int i = 0; i < vertCount; i++)
            {
                if (meshData.vertices != null && i < meshData.vertices.Count && meshData.vertices[i] != null && meshData.vertices[i].Length >= 3)
                {
                    float[] v = meshData.vertices[i];
                    vertices[i] = new Vector3(v[0], v[1], v[2]);
                }
                else if (meshData.flat_vertices != null && (i * 3 + 2) < meshData.flat_vertices.Length)
                {
                    vertices[i] = new Vector3(meshData.flat_vertices[i * 3], meshData.flat_vertices[i * 3 + 1], meshData.flat_vertices[i * 3 + 2]);
                }
                else
                {
                    vertices[i] = Vector3.zero;
                }

                // Normalized UV coordinates
                if (meshData.uvs != null && i < meshData.uvs.Count && meshData.uvs[i] != null && meshData.uvs[i].Length >= 2)
                {
                    uvs[i] = new Vector2(meshData.uvs[i][0], meshData.uvs[i][1]);
                }
                else if (meshData.flat_uvs != null && (i * 2 + 1) < meshData.flat_uvs.Length)
                {
                    uvs[i] = new Vector2(meshData.flat_uvs[i * 2], meshData.flat_uvs[i * 2 + 1]);
                }
                else
                {
                    uvs[i] = new Vector2(
                        width > 0 ? Mathf.Clamp01(vertices[i].x / width) : 0f,
                        length > 0 ? Mathf.Clamp01(vertices[i].z / length) : 0f
                    );
                }
            }

            mesh.vertices = vertices;
            mesh.uv = uvs;

            // Triangles / Indices
            if (meshData.indices != null && meshData.indices.Count > 0)
            {
                mesh.triangles = meshData.indices.ToArray();
            }
            else if (meshData.flat_indices != null && meshData.flat_indices.Length > 0)
            {
                mesh.triangles = meshData.flat_indices;
            }

            // Normals
            if (meshData.normals != null && meshData.normals.Count == vertCount)
            {
                Vector3[] normals = new Vector3[vertCount];
                for (int i = 0; i < vertCount; i++)
                {
                    if (meshData.normals[i] != null && meshData.normals[i].Length >= 3)
                        normals[i] = new Vector3(meshData.normals[i][0], meshData.normals[i][1], meshData.normals[i][2]);
                    else
                        normals[i] = Vector3.up;
                }
                mesh.normals = normals;
            }
            else if (meshData.flat_normals != null && meshData.flat_normals.Length == vertCount * 3)
            {
                Vector3[] normals = new Vector3[vertCount];
                for (int i = 0; i < vertCount; i++)
                {
                    normals[i] = new Vector3(meshData.flat_normals[i * 3], meshData.flat_normals[i * 3 + 1], meshData.flat_normals[i * 3 + 2]);
                }
                mesh.normals = normals;
            }
            else
            {
                mesh.RecalculateNormals();
            }

            mesh.RecalculateBounds();
            mesh.RecalculateTangents();

            GameObject go = new GameObject("AdaptiveTerrainMesh");
            go.transform.position = Vector3.zero;
            go.transform.rotation = Quaternion.identity;
            go.transform.localScale = Vector3.one;

            if (parentTransform != null)
                go.transform.SetParent(parentTransform, false);

            MeshFilter mf = go.AddComponent<MeshFilter>();
            mf.sharedMesh = mesh;

            MeshRenderer mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = CreateTerrainMaterial();

            MeshCollider mc = go.AddComponent<MeshCollider>();
            mc.sharedMesh = mesh;

#if UNITY_EDITOR
            Undo.RegisterCreatedObjectUndo(go, "Create AdaptiveTerrainMesh");
#endif

            return go;
        }

        public static Material CreateTerrainMaterial()
        {
            Material mat = new Material(Shader.Find("Standard"));
            mat.name = "AdaptiveTerrain_Material";
            mat.color = new Color(0.35f, 0.45f, 0.25f, 1.0f);
            return mat;
        }
    }

    #endregion

    #region Prefab Spawner & Asset Resolver

    /// <summary>
    /// Instantiates Synty prefabs with PrefabUtility.InstantiatePrefab (preserving live asset connections),
    /// organizes them into hierarchical zone containers, and provides fallback proxy cubes when assets are missing.
    /// </summary>
    public static class PrefabSpawner
    {
        private static Dictionary<string, string> s_prefabPathCache = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        public static void RefreshPrefabDatabase(string searchFolder = "Assets/PolygonMilitary/Prefabs")
        {
            s_prefabPathCache.Clear();

#if UNITY_EDITOR
            string[] searchFolders = Directory.Exists(searchFolder) ? new string[] { searchFolder } : new string[] { "Assets" };
            string[] guids = AssetDatabase.FindAssets("t:Prefab", searchFolders);

            foreach (string guid in guids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (string.IsNullOrEmpty(path)) continue;

                string filename = Path.GetFileNameWithoutExtension(path);
                if (!s_prefabPathCache.ContainsKey(filename))
                    s_prefabPathCache[filename] = path;

                // Also map full filename with extension
                string fullFilename = Path.GetFileName(path);
                if (!s_prefabPathCache.ContainsKey(fullFilename))
                    s_prefabPathCache[fullFilename] = path;
            }

            Debug.Log($"[WorldGen] Indexed {s_prefabPathCache.Count} prefabs in project.");
#endif
        }

        public static GameObject SpawnBuilding(BuildingManifest building, ZoneManifest zone, Transform zoneParentTransform, string searchFolder)
        {
            if (building == null) return null;

            if (s_prefabPathCache.Count == 0)
                RefreshPrefabDatabase(searchFolder);

            string prefabName = building.prefab_name;
            GameObject instance = null;
            bool isProxy = false;

#if UNITY_EDITOR
            // 1. Attempt to resolve prefab asset
            string assetPath = null;
            if (!string.IsNullOrEmpty(prefabName))
            {
                s_prefabPathCache.TryGetValue(prefabName, out assetPath);
                if (string.IsNullOrEmpty(assetPath))
                {
                    // Fallback search with t:Prefab
                    string[] guids = AssetDatabase.FindAssets($"{prefabName} t:Prefab");
                    if (guids != null && guids.Length > 0)
                        assetPath = AssetDatabase.GUIDToAssetPath(guids[0]);
                }
            }

            GameObject prefabAsset = !string.IsNullOrEmpty(assetPath) ? AssetDatabase.LoadAssetAtPath<GameObject>(assetPath) : null;

            if (prefabAsset != null)
            {
                // CRITICAL: Use PrefabUtility.InstantiatePrefab to maintain authentic project prefab link
                instance = (GameObject)PrefabUtility.InstantiatePrefab(prefabAsset, zoneParentTransform);
            }
            else
            {
                // Fallback: Create proxy cube representing building bounding box
                Debug.LogWarning($"[WorldGen] Prefab '{prefabName}' not found in '{searchFolder}'. Spawning fallback proxy cube.");
                instance = CreateProxyCube(building, zoneParentTransform);
                isProxy = true;
            }
#else
            // Runtime fallback
            instance = GameObject.CreatePrimitive(PrimitiveType.Cube);
            isProxy = true;
            if (zoneParentTransform != null) instance.transform.SetParent(zoneParentTransform, false);
#endif

            if (instance == null) return null;

            // 2. Set Transform attributes
            Vector3 pos = building.GetPosition();
            Quaternion rot = building.GetRotation();
            Vector3 scale = building.GetScale();

            instance.transform.position = pos;
            instance.transform.rotation = rot;
            if (isProxy)
            {
                BoundingBoxManifest bbox = building.GetBoundingBox();
                Vector3 bboxSize = bbox.GetSize();
                instance.transform.localScale = new Vector3(scale.x * bboxSize.x, scale.y * bboxSize.y, scale.z * bboxSize.z);
            }
            else
            {
                instance.transform.localScale = scale;
            }
            instance.name = string.IsNullOrEmpty(building.id) ? prefabName : $"{prefabName}_{building.id}";

#if UNITY_EDITOR
            Undo.RegisterCreatedObjectUndo(instance, "Spawn WorldGen Building");
#endif

            return instance;
        }

        private static GameObject CreateProxyCube(BuildingManifest building, Transform parentTransform)
        {
            GameObject proxy = GameObject.CreatePrimitive(PrimitiveType.Cube);
            proxy.name = $"{building.prefab_name}_Proxy";

            BoundingBoxManifest bbox = building.GetBoundingBox();
            Vector3 size = bbox.GetSize();
            Vector3 centerOffset = bbox.GetCenter();

            proxy.transform.localScale = size;
            if (parentTransform != null)
                proxy.transform.SetParent(parentTransform, false);

            // Give proxy a distinct semi-transparent or warning material
            Renderer rend = proxy.GetComponent<Renderer>();
            if (rend != null)
            {
                Material proxyMat = new Material(Shader.Find("Standard"));
                proxyMat.color = new Color(0.85f, 0.45f, 0.15f, 0.8f);
                rend.sharedMaterial = proxyMat;
            }

            return proxy;
        }
    }

    #endregion

    #region Material & Texture Swapper

    /// <summary>
    /// Dynamically swaps Synty PolygonMilitary materials and textures based on Zone Faction (A, B, C)
    /// and Destruction level (01, 02, 03, 04), preserving special materials (Glass, Vehicles, FX).
    /// </summary>
    public static class MaterialSwapper
    {
        private static Dictionary<string, Material> s_materialCache = new Dictionary<string, Material>(StringComparer.OrdinalIgnoreCase);
        private static Dictionary<string, Texture2D> s_textureCache = new Dictionary<string, Texture2D>(StringComparer.OrdinalIgnoreCase);

        public static void ClearCaches()
        {
            s_materialCache.Clear();
            s_textureCache.Clear();
        }

        public static void ApplyZoneTheme(GameObject buildingInstance, string faction, string destruction, string materialFolder = "Assets/PolygonMilitary/Materials", string textureFolder = "Assets/PolygonMilitary/Textures")
        {
            if (buildingInstance == null) return;

            string normalizedFaction = NormalizeFaction(faction);
            string normalizedDestruction = NormalizeDestruction(destruction);

            // Target Synty Material convention: PolygonMilitary_Mat_{destruction}_{faction}
            string targetMatName = $"PolygonMilitary_Mat_{normalizedDestruction}_{normalizedFaction}";
            Material targetMaterial = FindMaterialAsset(targetMatName, materialFolder);

            // Target Textures for dynamic fallback
            string targetAlbedoName = $"PolygonMilitary_Texture_{normalizedDestruction}_{normalizedFaction}";
            string targetNormalName = "PolygonMilitary_Texture_01_A_Normals";

            Texture2D albedoTex = FindTextureAsset(targetAlbedoName, textureFolder);
            Texture2D normalTex = FindTextureAsset(targetNormalName, textureFolder);

            Renderer[] renderers = buildingInstance.GetComponentsInChildren<Renderer>(true);
            foreach (Renderer rend in renderers)
            {
                Material[] sharedMats = rend.sharedMaterials;
                if (sharedMats == null || sharedMats.Length == 0) continue;

                bool modified = false;

                for (int i = 0; i < sharedMats.Length; i++)
                {
                    Material mat = sharedMats[i];
                    if (mat == null) continue;

                    string matName = mat.name;

                    // Selective Preservation: Skip glass, vehicle, decal, transparent, water, FX materials
                    if (IsProtectedMaterial(matName))
                        continue;

                    // Check if material is a base PolygonMilitary theme material
                    if (IsSwappableMaterial(matName))
                    {
                        if (targetMaterial != null)
                        {
                            sharedMats[i] = targetMaterial;
                            modified = true;
                        }
                        else
                        {
                            // Dynamic texture swap on existing material instance
                            if (albedoTex != null || normalTex != null)
                            {
                                Material clonedMat = new Material(mat);
                                clonedMat.name = $"{mat.name}_{normalizedDestruction}_{normalizedFaction}";
                                if (albedoTex != null) clonedMat.SetTexture("_MainTex", albedoTex);
                                if (normalTex != null)
                                {
                                    clonedMat.SetTexture("_BumpMap", normalTex);
                                    clonedMat.EnableKeyword("_NORMALMAP");
                                }
                                sharedMats[i] = clonedMat;
                                modified = true;
                            }
                        }
                    }
                }

                if (modified)
                {
                    rend.sharedMaterials = sharedMats;
#if UNITY_EDITOR
                    EditorUtility.SetDirty(rend);
#endif
                }
            }
        }

        public static bool IsProtectedMaterial(string materialName)
        {
            if (string.IsNullOrEmpty(materialName)) return false;
            string lower = materialName.ToLowerInvariant();
            return lower.Contains("glass") ||
                   lower.Contains("vehicle") ||
                   lower.Contains("decal") ||
                   lower.Contains("water") ||
                   lower.Contains("particle") ||
                   lower.Contains("fx") ||
                   lower.Contains("light") ||
                   lower.Contains("screen") ||
                   lower.Contains("ui");
        }

        public static bool IsSwappableMaterial(string materialName)
        {
            if (string.IsNullOrEmpty(materialName)) return false;
            string lower = materialName.ToLowerInvariant();
            return lower.Contains("polygonmilitary_mat") ||
                   lower.Contains("military_mat") ||
                   lower.Contains("polygon_mat") ||
                   lower.Contains("mat_01_a") ||
                   lower.Contains("mat_01_b") ||
                   lower.Contains("mat_01_c") ||
                   lower.Contains("mat_02_") ||
                   lower.Contains("mat_03_") ||
                   lower.Contains("mat_04_") ||
                   lower.Contains("standard");
        }

        public static string NormalizeFaction(string faction)
        {
            if (string.IsNullOrEmpty(faction)) return "A";
            string f = faction.Trim().ToUpperInvariant();
            if (f == "A" || f == "B" || f == "C") return f;
            if (f.EndsWith("A")) return "A";
            if (f.EndsWith("B")) return "B";
            if (f.EndsWith("C")) return "C";
            return "A";
        }

        public static string NormalizeDestruction(string destruction)
        {
            if (string.IsNullOrEmpty(destruction)) return "01";
            string d = destruction.Trim();
            if (d == "01" || d == "02" || d == "03" || d == "04") return d;
            if (d == "1") return "01";
            if (d == "2") return "02";
            if (d == "3") return "03";
            if (d == "4") return "04";
            return "01";
        }

        private static Material FindMaterialAsset(string matName, string searchFolder)
        {
            if (s_materialCache.TryGetValue(matName, out Material cached) && cached != null)
                return cached;

#if UNITY_EDITOR
            string[] guids = AssetDatabase.FindAssets($"{matName} t:Material", new string[] { searchFolder });
            if (guids == null || guids.Length == 0)
                guids = AssetDatabase.FindAssets($"{matName} t:Material");

            if (guids != null && guids.Length > 0)
            {
                string path = AssetDatabase.GUIDToAssetPath(guids[0]);
                Material mat = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (mat != null)
                {
                    s_materialCache[matName] = mat;
                    return mat;
                }
            }
#endif
            return null;
        }

        private static Texture2D FindTextureAsset(string texName, string searchFolder)
        {
            if (s_textureCache.TryGetValue(texName, out Texture2D cached) && cached != null)
                return cached;

#if UNITY_EDITOR
            string[] guids = AssetDatabase.FindAssets($"{texName} t:Texture2D", new string[] { searchFolder });
            if (guids == null || guids.Length == 0)
                guids = AssetDatabase.FindAssets($"{texName} t:Texture2D");

            if (guids != null && guids.Length > 0)
            {
                string path = AssetDatabase.GUIDToAssetPath(guids[0]);
                Texture2D tex = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
                if (tex != null)
                {
                    s_textureCache[texName] = tex;
                    return tex;
                }
            }
#endif
            return null;
        }
    }

    #endregion

    #region Road Mesh & Spline Builder

    /// <summary>
    /// Constructs smooth 3D road ribbon meshes and spline LineRenderers connecting zone waypoints,
    /// conforming vertically to terrain elevation with customizable width and surface textures.
    /// </summary>
    public static class RoadMeshBuilder
    {
        public static GameObject BuildRoad(RoadManifest road, Transform parentTransform, Terrain terrain, bool createRibbonMesh = true, bool createLineRenderer = true)
        {
            return BuildRoad(road, parentTransform, terrain, null, createRibbonMesh, createLineRenderer);
        }

        public static GameObject BuildRoad(RoadManifest road, Transform parentTransform, Terrain terrain, GameObject adaptiveTerrainMesh, bool createRibbonMesh = true, bool createLineRenderer = true)
        {
            if (road == null || road.waypoints == null || road.waypoints.Count < 2)
            {
                Debug.LogWarning($"[WorldGen] Road '{road?.id}' has fewer than 2 waypoints. Skipping.");
                return null;
            }

            GameObject roadGO = new GameObject(string.IsNullOrEmpty(road.id) ? "Road" : $"Road_{road.id}");
            roadGO.transform.position = Vector3.zero;
            roadGO.transform.rotation = Quaternion.identity;
            roadGO.transform.localScale = Vector3.one;

            if (parentTransform != null)
                roadGO.transform.SetParent(parentTransform, false);

            // 1. Collect & filter waypoints
            List<Vector3> points = new List<Vector3>();
            foreach (var wp in road.waypoints)
            {
                if (wp != null && wp.Length >= 3)
                {
                    Vector3 pt = new Vector3(wp[0], wp[1], wp[2]);
                    if (points.Count == 0 || Vector3.Distance(points[points.Count - 1], pt) > 0.1f)
                        points.Add(pt);
                }
            }

            if (points.Count < 2)
            {
                Debug.LogWarning($"[WorldGen] Road '{road.id}' has insufficient unique points after filtering.");
                return roadGO;
            }

            // 2. Sample smooth spline points using Catmull-Rom
            List<Vector3> splinePoints = SampleCatmullRomSpline(points, 60);

            // 3. Conform spline points to terrain with +0.15m elevation clearance to prevent z-fighting
            if (terrain != null)
            {
                for (int i = 0; i < splinePoints.Count; i++)
                {
                    Vector3 p = splinePoints[i];
                    float terrainHeight = terrain.SampleHeight(p);
                    p.y = Mathf.Max(p.y, terrainHeight + 0.15f);
                    splinePoints[i] = p;
                }
            }
            else if (adaptiveTerrainMesh != null)
            {
                for (int i = 0; i < splinePoints.Count; i++)
                {
                    Vector3 p = splinePoints[i];
                    p.y += 0.15f;
                    splinePoints[i] = p;
                }
            }

            float roadWidth = road.width > 0.5f ? road.width : 6.0f;

            // 4. Generate 3D Ribbon Quad Mesh
            if (createRibbonMesh)
            {
                Mesh roadMesh = GenerateRibbonMesh(splinePoints, roadWidth);
                MeshFilter mf = roadGO.AddComponent<MeshFilter>();
                mf.sharedMesh = roadMesh;

                MeshRenderer mr = roadGO.AddComponent<MeshRenderer>();
                mr.sharedMaterial = CreateRoadMaterial(road.surface_type);
            }

            // 5. Generate Companion Spline LineRenderer
            if (createLineRenderer)
            {
                LineRenderer lr = roadGO.AddComponent<LineRenderer>();
                lr.positionCount = splinePoints.Count;
                lr.SetPositions(splinePoints.ToArray());
                lr.startWidth = roadWidth;
                lr.endWidth = roadWidth;
                lr.useWorldSpace = true;
            }

#if UNITY_EDITOR
            Undo.RegisterCreatedObjectUndo(roadGO, "Build WorldGen Road");
#endif

            return roadGO;
        }

        public static List<Vector3> SampleCatmullRomSpline(List<Vector3> controlPoints, int samplesPerSegment = 10)
        {
            var spline = new List<Vector3>();
            int n = controlPoints.Count;
            if (n < 2) return controlPoints;

            for (int i = 0; i < n - 1; i++)
            {
                Vector3 p0 = i > 0 ? controlPoints[i - 1] : controlPoints[i] + (controlPoints[i] - controlPoints[i + 1]);
                Vector3 p1 = controlPoints[i];
                Vector3 p2 = controlPoints[i + 1];
                Vector3 p3 = (i + 2 < n) ? controlPoints[i + 2] : controlPoints[i + 1] + (controlPoints[i + 1] - controlPoints[i]);

                int steps = Mathf.Max(2, samplesPerSegment);
                for (int step = 0; step < steps; step++)
                {
                    float t = (float)step / steps;
                    spline.Add(EvaluateCatmullRom(p0, p1, p2, p3, t));
                }
            }

            // Add final endpoint
            spline.Add(controlPoints[n - 1]);
            return spline;
        }

        private static Vector3 EvaluateCatmullRom(Vector3 p0, Vector3 p1, Vector3 p2, Vector3 p3, float t)
        {
            float t2 = t * t;
            float t3 = t2 * t;

            return 0.5f * (
                (2f * p1) +
                (-p0 + p2) * t +
                (2f * p0 - 5f * p1 + 4f * p2 - p3) * t2 +
                (-p0 + 3f * p1 - 3f * p2 + p3) * t3
            );
        }

        public static Mesh GenerateRibbonMesh(List<Vector3> splinePoints, float width)
        {
            Mesh mesh = new Mesh();
            mesh.name = "Road_Ribbon_Mesh";

            int count = splinePoints.Count;
            if (count < 2) return mesh;

            int vertCount = count * 2;
            int quadCount = count - 1;
            int triCount = quadCount * 6;

            Vector3[] vertices = new Vector3[vertCount];
            Vector3[] normals = new Vector3[vertCount];
            Vector2[] uvs = new Vector2[vertCount];
            Vector4[] tangents = new Vector4[vertCount];
            int[] triangles = new int[triCount];

            float halfWidth = width * 0.5f;
            float accumulatedDist = 0f;

            for (int i = 0; i < count; i++)
            {
                Vector3 pt = splinePoints[i];
                Vector3 forward;

                if (i == 0)
                    forward = (splinePoints[1] - pt).normalized;
                else if (i == count - 1)
                    forward = (pt - splinePoints[i - 1]).normalized;
                else
                    forward = (splinePoints[i + 1] - splinePoints[i - 1]).normalized;

                if (i > 0)
                    accumulatedDist += Vector3.Distance(splinePoints[i - 1], pt);

                Vector3 right = Vector3.Cross(Vector3.up, forward).normalized;
                if (right.sqrMagnitude < 0.01f)
                    right = Vector3.right;

                int vLeft = i * 2;
                int vRight = i * 2 + 1;

                vertices[vLeft] = pt - right * halfWidth;
                vertices[vRight] = pt + right * halfWidth;

                normals[vLeft] = Vector3.up;
                normals[vRight] = Vector3.up;

                float vCoord = accumulatedDist / width;
                uvs[vLeft] = new Vector2(0f, vCoord);
                uvs[vRight] = new Vector2(1f, vCoord);

                Vector4 tan = new Vector4(forward.x, forward.y, forward.z, 1f);
                tangents[vLeft] = tan;
                tangents[vRight] = tan;

                if (i < quadCount)
                {
                    int triIdx = i * 6;
                    triangles[triIdx + 0] = vLeft;
                    triangles[triIdx + 1] = vLeft + 2;
                    triangles[triIdx + 2] = vRight;

                    triangles[triIdx + 3] = vRight;
                    triangles[triIdx + 4] = vLeft + 2;
                    triangles[triIdx + 5] = vRight + 2;
                }
            }

            mesh.vertices = vertices;
            mesh.normals = normals;
            mesh.uv = uvs;
            mesh.tangents = tangents;
            mesh.triangles = triangles;
            mesh.RecalculateBounds();

            return mesh;
        }

        private static Material CreateRoadMaterial(string surfaceType)
        {
            Material mat = new Material(Shader.Find("Standard"));
            if (surfaceType != null && surfaceType.ToLowerInvariant().Contains("dirt"))
            {
                mat.color = new Color(0.48f, 0.38f, 0.28f, 1f); // Dirt brown
            }
            else
            {
                mat.color = new Color(0.18f, 0.19f, 0.21f, 1f); // Asphalt dark slate
            }
            return mat;
        }
    }

    #endregion

    #region Editor Window & Importer Orchestrator

#if UNITY_EDITOR
    public enum TerrainImportMode
    {
        AdaptiveDecimatedMesh,
        StandardTerrain,
        HybridBoth
    }

    /// <summary>
    /// Custom Unity EditorWindow providing a rich graphical interface for importing world_manifest.json,
    /// configuring search paths, toggling features, and managing procedural scene generation.
    /// </summary>
    public class WorldManifestImporterWindow : EditorWindow
    {
        private string manifestFilePath = "world_manifest.json";
        private string prefabSearchFolder = "Assets/PolygonMilitary/Prefabs";
        private string materialSearchFolder = "Assets/PolygonMilitary/Materials";
        private string textureSearchFolder = "Assets/PolygonMilitary/Textures";

        private bool importTerrain = true;
        private TerrainImportMode terrainImportMode = TerrainImportMode.AdaptiveDecimatedMesh;
        private bool importBuildings = true;
        private bool applyMaterials = true;
        private bool importRoads = true;
        private bool generateRoadRibbon = true;
        private bool generateRoadLineRenderer = true;
        private bool clearPreviousWorld = true;
        private bool autoFrameScene = true;

        private Vector2 scrollPos;
        private WorldManifest cachedManifest = null;
        private string validationStatus = "No manifest loaded.";
        private MessageType statusMessageType = MessageType.Info;

        [MenuItem("WorldGen/Import World Manifest", false, 10)]
        [MenuItem("WorldGen/Import Manifest...", false, 11)]
        public static void ShowWindow()
        {
            var window = GetWindow<WorldManifestImporterWindow>("World Manifest Importer", true);
            window.minSize = new Vector2(460, 580);
            window.Show();
        }

        [MenuItem("WorldGen/Clear Generated World", false, 20)]
        public static void ClearGeneratedWorldMenu()
        {
            GameObject existingRoot = GameObject.Find("[WorldGen_Output]");
            if (existingRoot != null)
            {
                if (EditorUtility.DisplayDialog("Clear Generated World", "Are you sure you want to delete '[WorldGen_Output]' and all procedural objects?", "Yes, Delete", "Cancel"))
                {
                    Undo.DestroyObjectImmediate(existingRoot);
                    Debug.Log("[WorldGen] Cleared '[WorldGen_Output]' from scene.");
                }
            }
            else
            {
                EditorUtility.DisplayDialog("Clear Generated World", "No '[WorldGen_Output]' found in active scene.", "OK");
            }
        }

        private void OnGUI()
        {
            scrollPos = EditorGUILayout.BeginScrollView(scrollPos);

            // Title Header
            DrawHeader();

            EditorGUILayout.Space(10);

            // Manifest File Selector
            DrawFileSelectionSection();

            EditorGUILayout.Space(10);

            // Search Folders Configuration
            DrawFolderConfigurationSection();

            EditorGUILayout.Space(10);

            // Feature Options Toggles
            DrawOptionsSection();

            EditorGUILayout.Space(10);

            // Manifest Summary / Status Box
            DrawSummaryBox();

            EditorGUILayout.Space(15);

            // Action Buttons
            DrawActionButtons();

            EditorGUILayout.EndScrollView();
        }

        private void DrawHeader()
        {
            EditorGUILayout.BeginVertical(EditorStyles.helpBox);
            GUIStyle headerStyle = new GUIStyle(EditorStyles.boldLabel)
            {
                fontSize = 15,
                alignment = TextAnchor.MiddleCenter
            };
            EditorGUILayout.LabelField("Procedural World Manifest Importer", headerStyle);
            EditorGUILayout.LabelField("Synty PolygonMilitary & Procedural Terrain Pipeline", EditorStyles.centeredGreyMiniLabel);
            EditorGUILayout.EndVertical();
        }

        private void DrawFileSelectionSection()
        {
            EditorGUILayout.LabelField("Manifest File Source", EditorStyles.boldLabel);
            EditorGUILayout.BeginHorizontal();
            manifestFilePath = EditorGUILayout.TextField("Manifest Path", manifestFilePath);
            if (GUILayout.Button("Browse...", GUILayout.Width(75)))
            {
                string selected = EditorUtility.OpenFilePanel("Select World Manifest JSON", Application.dataPath, "json");
                if (!string.IsNullOrEmpty(selected))
                {
                    manifestFilePath = selected;
                    LoadAndValidateManifest();
                }
            }
            EditorGUILayout.EndHorizontal();

            if (GUILayout.Button("Load & Validate Manifest", EditorStyles.miniButton))
            {
                LoadAndValidateManifest();
            }
        }

        private void DrawFolderConfigurationSection()
        {
            EditorGUILayout.LabelField("Synty Asset Search Folders", EditorStyles.boldLabel);
            prefabSearchFolder = EditorGUILayout.TextField("Prefabs Folder", prefabSearchFolder);
            materialSearchFolder = EditorGUILayout.TextField("Materials Folder", materialSearchFolder);
            textureSearchFolder = EditorGUILayout.TextField("Textures Folder", textureSearchFolder);
        }

        private void DrawOptionsSection()
        {
            EditorGUILayout.LabelField("Import Pipeline Options", EditorStyles.boldLabel);
            importTerrain = EditorGUILayout.Toggle("Import Terrain", importTerrain);
            if (importTerrain)
            {
                EditorGUI.indentLevel++;
                terrainImportMode = (TerrainImportMode)EditorGUILayout.EnumPopup("Terrain Mode", terrainImportMode);
                EditorGUI.indentLevel--;
            }
            importBuildings = EditorGUILayout.Toggle("Import Buildings & Prefabs", importBuildings);
            applyMaterials = EditorGUILayout.Toggle("Apply Faction & Damage Materials", applyMaterials);
            importRoads = EditorGUILayout.Toggle("Import Roads", importRoads);
            if (importRoads)
            {
                EditorGUI.indentLevel++;
                generateRoadRibbon = EditorGUILayout.Toggle("Generate 3D Ribbon Mesh", generateRoadRibbon);
                generateRoadLineRenderer = EditorGUILayout.Toggle("Generate LineRenderer Spline", generateRoadLineRenderer);
                EditorGUI.indentLevel--;
            }
            clearPreviousWorld = EditorGUILayout.Toggle("Clear Previous Import First", clearPreviousWorld);
            autoFrameScene = EditorGUILayout.Toggle("Auto-Frame Scene View", autoFrameScene);
        }

        private void DrawSummaryBox()
        {
            EditorGUILayout.LabelField("Manifest Summary & Validation", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(validationStatus, statusMessageType);
        }

        private void DrawActionButtons()
        {
            GUI.backgroundColor = new Color(0.2f, 0.75f, 0.35f, 1f);
            if (GUILayout.Button("IMPORT WORLD MANIFEST", GUILayout.Height(36)))
            {
                ExecuteImport();
            }
            GUI.backgroundColor = Color.white;

            EditorGUILayout.Space(4);

            if (GUILayout.Button("Clear Generated World", GUILayout.Height(24)))
            {
                ClearGeneratedWorldMenu();
            }
        }

        private void LoadAndValidateManifest()
        {
            try
            {
                string resolvedPath = ResolvePath(manifestFilePath);
                if (!File.Exists(resolvedPath))
                {
                    validationStatus = $"File not found at: {resolvedPath}";
                    statusMessageType = MessageType.Error;
                    cachedManifest = null;
                    return;
                }

                string json = File.ReadAllText(resolvedPath);
                cachedManifest = ManifestJsonParser.Parse(json);

                int zoneCount = cachedManifest.zones.Count;
                int bldCount = cachedManifest.buildings.Count;
                int roadCount = cachedManifest.roads.Count;
                float w = cachedManifest.terrain.GetWidth();
                float l = cachedManifest.terrain.GetLength();
                float h = cachedManifest.terrain.GetHeightScale();

                validationStatus = $"Valid Manifest Loaded!\n" +
                                   $"Seed: {cachedManifest.metadata.seed} | Version: {cachedManifest.metadata.generator_version}\n" +
                                   $"Terrain: {w}m x {h}m x {l}m (Res: {cachedManifest.terrain.resolution})\n" +
                                   $"Zones: {zoneCount} | Buildings: {bldCount} | Roads: {roadCount}";
                statusMessageType = MessageType.Info;
            }
            catch (Exception ex)
            {
                validationStatus = $"Validation Failed: {ex.Message}";
                statusMessageType = MessageType.Error;
                cachedManifest = null;
            }
        }

        public void ExecuteImport()
        {
            try
            {
                string resolvedPath = ResolvePath(manifestFilePath);
                if (!File.Exists(resolvedPath))
                {
                    EditorUtility.DisplayDialog("Import Error", $"Manifest file not found:\n{resolvedPath}", "OK");
                    return;
                }

                EditorUtility.DisplayProgressBar("WorldGen Importer", "Reading manifest JSON...", 0.05f);
                string json = File.ReadAllText(resolvedPath);
                WorldManifest manifest = ManifestJsonParser.Parse(json);

                // 1. Clear previous world if requested
                if (clearPreviousWorld)
                {
                    GameObject existingRoot = GameObject.Find("[WorldGen_Output]");
                    if (existingRoot != null)
                        Undo.DestroyObjectImmediate(existingRoot);
                }

                // 2. Create Root Hierarchy GameObject
                GameObject rootGO = new GameObject("[WorldGen_Output]");
                Undo.RegisterCreatedObjectUndo(rootGO, "Create WorldGen Root");

                Terrain terrainInstance = null;
                GameObject adaptiveTerrainGO = null;

                // 3. Import Terrain
                if (importTerrain && manifest.terrain != null)
                {
                    EditorUtility.DisplayProgressBar("WorldGen Importer", "Generating Terrain Data...", 0.2f);
                    GameObject terrainRoot = new GameObject("Terrain");
                    terrainRoot.transform.SetParent(rootGO.transform, false);
                    Undo.RegisterCreatedObjectUndo(terrainRoot, "Create Terrain Parent");

                    bool hasAdaptiveMesh = manifest.terrain.mesh != null &&
                        ((manifest.terrain.mesh.vertices != null && manifest.terrain.mesh.vertices.Count > 0) ||
                         (manifest.terrain.mesh.flat_vertices != null && manifest.terrain.mesh.flat_vertices.Length > 0));

                    bool hasHeightmap = manifest.terrain.raw_heightmap_2d != null ||
                        (manifest.terrain.raw_heightmap_1d != null && manifest.terrain.raw_heightmap_1d.Length > 0);

                    if ((terrainImportMode == TerrainImportMode.AdaptiveDecimatedMesh || terrainImportMode == TerrainImportMode.HybridBoth) && hasAdaptiveMesh)
                    {
                        adaptiveTerrainGO = AdaptiveMeshGenerator.BuildAdaptiveMesh(manifest.terrain, terrainRoot.transform);
                    }

                    if ((terrainImportMode == TerrainImportMode.StandardTerrain || terrainImportMode == TerrainImportMode.HybridBoth || (!hasAdaptiveMesh && hasHeightmap)) && hasHeightmap)
                    {
                        TerrainGenerator.BuildTerrain(manifest.terrain, terrainRoot.transform, out terrainInstance);
                    }
                }

                // 4. Index Prefab Assets
                if (importBuildings && manifest.buildings != null && manifest.buildings.Count > 0)
                {
                    EditorUtility.DisplayProgressBar("WorldGen Importer", "Indexing Synty Prefabs...", 0.35f);
                    PrefabSpawner.RefreshPrefabDatabase(prefabSearchFolder);

                    // Build lookup map for zones
                    Dictionary<string, ZoneManifest> zoneMap = new Dictionary<string, ZoneManifest>(StringComparer.OrdinalIgnoreCase);
                    foreach (var z in manifest.zones)
                    {
                        if (!string.IsNullOrEmpty(z.id))
                            zoneMap[z.id] = z;
                    }

                    // Create Zones Root
                    GameObject zonesRoot = new GameObject("Zones");
                    zonesRoot.transform.SetParent(rootGO.transform, false);
                    Undo.RegisterCreatedObjectUndo(zonesRoot, "Create Zones Parent");

                    // Create Zone Sub-Parents
                    Dictionary<string, Transform> zoneTransforms = new Dictionary<string, Transform>(StringComparer.OrdinalIgnoreCase);
                    foreach (var z in manifest.zones)
                    {
                        string zName = $"Zone_{z.id}_Faction{z.GetNormalizedFaction()}_Destruction{z.GetNormalizedDestruction()}";
                        GameObject zGO = new GameObject(zName);
                        zGO.transform.SetParent(zonesRoot.transform, false);
                        Undo.RegisterCreatedObjectUndo(zGO, "Create Zone Parent");
                        zoneTransforms[z.id] = zGO.transform;

                        // Attach ZoneMetadata component
                        ZoneMetadata meta = zGO.AddComponent<ZoneMetadata>();
                        meta.zoneId = z.id;
                        meta.zoneName = z.name;
                        meta.zoneType = !string.IsNullOrEmpty(z.zone_type) ? z.zone_type : "military_base";
                        meta.faction = z.GetNormalizedFaction();
                        meta.destruction = z.GetNormalizedDestruction();
                        meta.density = z.density > 0 ? z.density : z.building_density;
                        meta.radius = z.radius;
                        meta.center = z.GetCenterVector();
                    }

                    // Spawn Buildings
                    int totalBlds = manifest.buildings.Count;
                    for (int i = 0; i < totalBlds; i++)
                    {
                        var b = manifest.buildings[i];
                        float progress = 0.4f + (0.35f * ((float)i / totalBlds));
                        EditorUtility.DisplayProgressBar("WorldGen Importer", $"Spawning Building {i + 1}/{totalBlds} ({b.prefab_name})...", progress);

                        Transform zoneParent = zonesRoot.transform;
                        ZoneManifest zManifest = null;
                        if (!string.IsNullOrEmpty(b.zone_id) && zoneTransforms.TryGetValue(b.zone_id, out Transform zTrans))
                        {
                            zoneParent = zTrans;
                            zoneMap.TryGetValue(b.zone_id, out zManifest);
                        }

                        // District Hierarchy
                        Transform buildingParent = zoneParent;
                        string districtKey = !string.IsNullOrEmpty(b.district_id) ? b.district_id :
                                             (!string.IsNullOrEmpty(b.sub_district) ? b.sub_district :
                                             (!string.IsNullOrEmpty(b.placement_role) ? b.placement_role : ""));

                        if (!string.IsNullOrEmpty(districtKey) && zoneParent != zonesRoot.transform)
                        {
                            string districtName = districtKey.StartsWith("District_", StringComparison.OrdinalIgnoreCase) ? districtKey : $"District_{districtKey}";
                            Transform existingDistrict = null;
                            foreach (Transform child in zoneParent)
                            {
                                if (string.Equals(child.gameObject.name, districtName, StringComparison.OrdinalIgnoreCase))
                                {
                                    existingDistrict = child;
                                    break;
                                }
                            }

                            if (existingDistrict == null)
                            {
                                GameObject districtGO = new GameObject(districtName);
                                districtGO.transform.SetParent(zoneParent, false);
                                Undo.RegisterCreatedObjectUndo(districtGO, "Create District Parent");
                                existingDistrict = districtGO.transform;
                            }
                            buildingParent = existingDistrict;
                        }

                        GameObject bldInstance = PrefabSpawner.SpawnBuilding(b, zManifest, buildingParent, prefabSearchFolder);

                        // Material & Texture Swapping
                        if (applyMaterials && bldInstance != null)
                        {
                            string faction = !string.IsNullOrEmpty(b.faction) ? b.faction : (zManifest != null ? zManifest.faction : "A");
                            string destruction = !string.IsNullOrEmpty(b.destruction) ? b.destruction : (zManifest != null ? zManifest.destruction : "01");
                            MaterialSwapper.ApplyZoneTheme(bldInstance, faction, destruction, materialSearchFolder, textureSearchFolder);
                        }
                    }
                }

                // 5. Import Roads
                if (importRoads && manifest.roads != null && manifest.roads.Count > 0)
                {
                    EditorUtility.DisplayProgressBar("WorldGen Importer", "Generating Roads & Splines...", 0.85f);
                    GameObject roadsRoot = new GameObject("Roads");
                    roadsRoot.transform.SetParent(rootGO.transform, false);
                    Undo.RegisterCreatedObjectUndo(roadsRoot, "Create Roads Parent");

                    foreach (var road in manifest.roads)
                    {
                        RoadMeshBuilder.BuildRoad(road, roadsRoot.transform, terrainInstance, adaptiveTerrainGO, generateRoadRibbon, generateRoadLineRenderer);
                    }
                }

                EditorUtility.DisplayProgressBar("WorldGen Importer", "Finalizing scene...", 0.98f);
                Selection.activeGameObject = rootGO;

                if (autoFrameScene && SceneView.lastActiveSceneView != null)
                {
                    SceneView.lastActiveSceneView.FrameSelected();
                }

                Debug.Log($"[WorldGen] Successfully imported procedural world from '{manifestFilePath}'!");
                EditorUtility.DisplayDialog("WorldGen Import Complete", $"Successfully imported:\n- Terrain ({manifest.terrain.GetWidth()}x{manifest.terrain.GetLength()}m)\n- {manifest.zones.Count} Zones\n- {manifest.buildings.Count} Buildings\n- {manifest.roads.Count} Road Splines", "OK");
            }
            catch (Exception ex)
            {
                Debug.LogError($"[WorldGen] Import Failed: {ex}");
                EditorUtility.DisplayDialog("Import Error", $"An error occurred during import:\n{ex.Message}", "OK");
            }
            finally
            {
                EditorUtility.ClearProgressBar();
            }
        }

        private string ResolvePath(string path)
        {
            if (string.IsNullOrEmpty(path)) return "";
            if (Path.IsPathRooted(path)) return path;

            // Check relative to Application.dataPath
            string inAssets = Path.Combine(Application.dataPath, path);
            if (File.Exists(inAssets)) return inAssets;

            // Check relative to Project Root (parent of Assets)
            string projectRoot = Path.GetDirectoryName(Application.dataPath);
            string inRoot = Path.Combine(projectRoot, path);
            if (File.Exists(inRoot)) return inRoot;

            return path;
        }
    }
#endif

    #endregion
}
