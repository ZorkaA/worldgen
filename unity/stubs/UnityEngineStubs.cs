// Stub definitions for UnityEngine assemblies to allow offline C# compilation and automated verification
using System;
using System.Collections.Generic;

namespace UnityEngine
{
    public struct Vector2
    {
        public float x, y;
        public Vector2(float x, float y) { this.x = x; this.y = y; }
        public static Vector2 zero => new Vector2(0, 0);
        public static Vector2 one => new Vector2(1, 1);
        public static Vector2 operator +(Vector2 a, Vector2 b) => new Vector2(a.x + b.x, a.y + b.y);
        public static Vector2 operator -(Vector2 a, Vector2 b) => new Vector2(a.x - b.x, a.y - b.y);
        public static Vector2 operator *(Vector2 a, float d) => new Vector2(a.x * d, a.y * d);
        public static Vector2 operator *(float d, Vector2 a) => new Vector2(a.x * d, a.y * d);
        public static float Distance(Vector2 a, Vector2 b) => (float)Math.Sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y));
    }

    public struct Vector3
    {
        public float x, y, z;
        public Vector3(float x, float y, float z) { this.x = x; this.y = y; this.z = z; }
        public static Vector3 zero => new Vector3(0, 0, 0);
        public static Vector3 one => new Vector3(1, 1, 1);
        public static Vector3 up => new Vector3(0, 1, 0);
        public static Vector3 right => new Vector3(1, 0, 0);
        public static Vector3 forward => new Vector3(0, 0, 1);
        public static Vector3 operator +(Vector3 a, Vector3 b) => new Vector3(a.x + b.x, a.y + b.y, a.z + b.z);
        public static Vector3 operator -(Vector3 a, Vector3 b) => new Vector3(a.x - b.x, a.y - b.y, a.z - b.z);
        public static Vector3 operator -(Vector3 a) => new Vector3(-a.x, -a.y, -a.z);
        public static Vector3 operator *(Vector3 a, float d) => new Vector3(a.x * d, a.y * d, a.z * d);
        public static Vector3 operator *(float d, Vector3 a) => new Vector3(a.x * d, a.y * d, a.z * d);
        public static Vector3 operator /(Vector3 a, float d) => new Vector3(a.x / d, a.y / d, a.z / d);
        public static Vector3 Cross(Vector3 lhs, Vector3 rhs) => new Vector3(lhs.y * rhs.z - lhs.z * rhs.y, lhs.z * rhs.x - lhs.x * rhs.z, lhs.x * rhs.y - lhs.y * rhs.x);
        public static float Dot(Vector3 lhs, Vector3 rhs) => lhs.x * rhs.x + lhs.y * rhs.y + lhs.z * rhs.z;
        public float magnitude => (float)Math.Sqrt(x * x + y * y + z * z);
        public float sqrMagnitude => x * x + y * y + z * z;
        public Vector3 normalized => magnitude > 1e-5f ? this / magnitude : zero;
        public static float Distance(Vector3 a, Vector3 b) => (a - b).magnitude;
        public override string ToString() => $"({x:F2}, {y:F2}, {z:F2})";
    }

    public struct Vector4
    {
        public float x, y, z, w;
        public Vector4(float x, float y, float z, float w) { this.x = x; this.y = y; this.z = z; this.w = w; }
        public static Vector4 zero => new Vector4(0, 0, 0, 0);
    }

    public struct Quaternion
    {
        public float x, y, z, w;
        public Quaternion(float x, float y, float z, float w) { this.x = x; this.y = y; this.z = z; this.w = w; }
        public static Quaternion identity => new Quaternion(0, 0, 0, 1);
        public static Quaternion Euler(float x, float y, float z) => identity;
        public static Quaternion Euler(Vector3 euler) => Euler(euler.x, euler.y, euler.z);
        public static Quaternion LookRotation(Vector3 forward, Vector3 upwards) => identity;
        public static Quaternion LookRotation(Vector3 forward) => identity;
        public Vector3 eulerAngles => Vector3.zero;
    }

    public struct Color
    {
        public float r, g, b, a;
        public Color(float r, float g, float b, float a = 1f) { this.r = r; this.g = b; this.b = b; this.a = a; }
        public static Color white => new Color(1, 1, 1, 1);
        public static Color black => new Color(0, 0, 0, 1);
        public static Color red => new Color(1, 0, 0, 1);
        public static Color green => new Color(0, 1, 0, 1);
        public static Color blue => new Color(0, 0, 1, 1);
        public static Color yellow => new Color(1, 0.92f, 0.016f, 1);
        public static Color gray => new Color(0.5f, 0.5f, 0.5f, 1);
        public static Color clear => new Color(0, 0, 0, 0);
    }

    public struct Bounds
    {
        public Vector3 center { get; set; }
        public Vector3 size { get; set; }
        public Bounds(Vector3 center, Vector3 size) { this.center = center; this.size = size; }
    }

    public static class Mathf
    {
        public const float PI = 3.14159265358979323846f;
        public static float Clamp01(float value) => value < 0f ? 0f : (value > 1f ? 1f : value);
        public static float Clamp(float value, float min, float max) => value < min ? min : (value > max ? max : value);
        public static int Clamp(int value, int min, int max) => value < min ? min : (value > max ? max : value);
        public static float Lerp(float a, float b, float t) => a + (b - a) * Clamp01(t);
        public static float Min(float a, float b) => a < b ? a : b;
        public static float Max(float a, float b) => a > b ? a : b;
        public static int Min(int a, int b) => a < b ? a : b;
        public static int Max(int a, int b) => a > b ? a : b;
        public static int FloorToInt(float f) => (int)Math.Floor(f);
        public static int CeilToInt(float f) => (int)Math.Ceiling(f);
        public static int RoundToInt(float f) => (int)Math.Round(f);
        public static float Abs(float f) => Math.Abs(f);
        public static float Sqrt(float f) => (float)Math.Sqrt(f);
        public static bool IsPowerOfTwo(int value) => (value & (value - 1)) == 0 && value > 0;
        public static int NextPowerOfTwo(int value)
        {
            int v = 1;
            while (v < value) v <<= 1;
            return v;
        }
    }

    public class Object
    {
        public string name { get; set; } = "";
        public static void DestroyImmediate(Object obj) { }
        public static Object Instantiate(Object original) => original;
        public static Object Instantiate(Object original, Transform parent) => original;
        public static T Instantiate<T>(T original) where T : Object => original;
        public static T Instantiate<T>(T original, Transform parent) where T : Object => original;
    }

    public class Component : Object
    {
        public GameObject gameObject { get; set; }
        public Transform transform => gameObject?.transform;
        public T GetComponent<T>() where T : Component => gameObject?.GetComponent<T>();
        public T[] GetComponentsInChildren<T>(bool includeInactive = false) where T : Component => gameObject?.GetComponentsInChildren<T>(includeInactive) ?? new T[0];
    }

    public class Transform : Component, System.Collections.IEnumerable
    {
        public Vector3 position { get; set; } = Vector3.zero;
        public Vector3 localPosition { get; set; } = Vector3.zero;
        public Quaternion rotation { get; set; } = Quaternion.identity;
        public Quaternion localRotation { get; set; } = Quaternion.identity;
        public Vector3 localScale { get; set; } = Vector3.one;
        public Transform parent { get; set; }
        public int childCount => children.Count;
        private List<Transform> children = new List<Transform>();

        public void SetParent(Transform parent, bool worldPositionStays = true)
        {
            this.parent?.children.Remove(this);
            this.parent = parent;
            parent?.children.Add(this);
        }

        public Transform GetChild(int index) => children[index];
        public System.Collections.IEnumerator GetEnumerator() => children.GetEnumerator();
    }

    public class GameObject : Object
    {
        public Transform transform { get; }
        public bool activeSelf { get; set; } = true;
        public int layer { get; set; } = 0;
        public string tag { get; set; } = "Untagged";
        private List<Component> components = new List<Component>();

        public GameObject()
        {
            transform = new Transform { gameObject = this };
            components.Add(transform);
        }

        public GameObject(string name) : this()
        {
            this.name = name;
        }

        public T AddComponent<T>() where T : Component, new()
        {
            var comp = new T { gameObject = this };
            components.Add(comp);
            return comp;
        }

        public T GetComponent<T>() where T : Component
        {
            foreach (var c in components)
            {
                if (c is T match) return match;
            }
            return null;
        }

        public T[] GetComponentsInChildren<T>(bool includeInactive = false) where T : Component
        {
            var list = new List<T>();
            CollectComponentsInChildren(this, list, includeInactive);
            return list.ToArray();
        }

        private static void CollectComponentsInChildren<T>(GameObject go, List<T> list, bool includeInactive) where T : Component
        {
            if (!go.activeSelf && !includeInactive) return;
            foreach (var c in go.components)
            {
                if (c is T match) list.Add(match);
            }
            foreach (Transform child in go.transform)
            {
                CollectComponentsInChildren(child.gameObject, list, includeInactive);
            }
        }

        public static GameObject CreatePrimitive(PrimitiveType type)
        {
            var go = new GameObject(type.ToString());
            go.AddComponent<MeshFilter>();
            go.AddComponent<MeshRenderer>();
            return go;
        }

        public static GameObject Find(string name) => null;
    }

    public enum PrimitiveType
    {
        Sphere, Capsule, Cylinder, Cube, Plane, Quad
    }

    public class TerrainData : Object
    {
        public int heightmapResolution { get; set; } = 513;
        public Vector3 size { get; set; } = new Vector3(1000, 150, 1000);
        public float[,] heightsData;

        public void SetHeights(int xBase, int yBase, float[,] heights)
        {
            this.heightsData = heights;
        }

        public float[,] GetHeights(int xBase, int yBase, int width, int height)
        {
            return heightsData ?? new float[height, width];
        }

        public float GetHeight(int x, int z) => 0f;
        public float GetInterpolatedHeight(float xNorm, float zNorm) => 0f;
    }

    public class Terrain : Component
    {
        public TerrainData terrainData { get; set; }
        public static GameObject CreateTerrainGameObject(TerrainData terrainData)
        {
            var go = new GameObject("Terrain");
            var terrain = go.AddComponent<Terrain>();
            terrain.terrainData = terrainData;
            var collider = go.AddComponent<TerrainCollider>();
            collider.terrainData = terrainData;
            return go;
        }
        public static Terrain activeTerrain => null;
        public float SampleHeight(Vector3 worldPosition) => 0f;
    }

    public class TerrainCollider : Component
    {
        public TerrainData terrainData { get; set; }
    }

    public class Shader : Object
    {
        public static Shader Find(string name) => new Shader { name = name };
    }

    public class Texture : Object { }
    public class Texture2D : Texture
    {
        public int width { get; set; }
        public int height { get; set; }
        public Texture2D(int width, int height) { this.width = width; this.height = height; }
    }

    public class Material : Object
    {
        public Shader shader { get; set; }
        public Color color { get; set; } = Color.white;
        public Texture mainTexture { get; set; }
        private Dictionary<string, object> properties = new Dictionary<string, object>();

        public Material(Shader shader) { this.shader = shader; }
        public Material(Material source) { this.shader = source?.shader; }

        public void SetTexture(string name, Texture value) => properties[name] = value;
        public Texture GetTexture(string name) => properties.ContainsKey(name) ? properties[name] as Texture : null;
        public void SetColor(string name, Color value) => properties[name] = value;
        public void SetFloat(string name, float value) => properties[name] = value;
        public void EnableKeyword(string keyword) { }
    }

    public class Renderer : Component
    {
        public Material sharedMaterial { get; set; }
        public Material[] sharedMaterials { get; set; } = new Material[0];
        public Material material { get; set; }
        public Material[] materials { get; set; } = new Material[0];
        public bool enabled { get; set; } = true;
    }

    public class MeshRenderer : Renderer { }
    public class SkinnedMeshRenderer : Renderer { }

    public class Mesh : Object
    {
        public Vector3[] vertices { get; set; } = new Vector3[0];
        public int[] triangles { get; set; } = new int[0];
        public Vector3[] normals { get; set; } = new Vector3[0];
        public Vector2[] uv { get; set; } = new Vector2[0];
        public Vector4[] tangents { get; set; } = new Vector4[0];
        public void RecalculateNormals() { }
        public void RecalculateBounds() { }
        public void RecalculateTangents() { }
        public void Clear() { }
    }

    public class MeshFilter : Component
    {
        public Mesh sharedMesh { get; set; }
        public Mesh mesh { get; set; }
    }

    public class LineRenderer : Renderer
    {
        public int positionCount { get; set; }
        public float startWidth { get; set; }
        public float endWidth { get; set; }
        public bool useWorldSpace { get; set; } = true;
        public void SetPositions(Vector3[] positions) { }
        public void SetPosition(int index, Vector3 position) { }
    }

    public class MaterialPropertyBlock
    {
        private Dictionary<string, object> props = new Dictionary<string, object>();
        public void SetTexture(string name, Texture value) => props[name] = value;
        public void SetColor(string name, Color value) => props[name] = value;
        public void Clear() => props.Clear();
    }

    public static class Debug
    {
        public static void Log(object message) => Console.WriteLine($"[Info] {message}");
        public static void LogWarning(object message) => Console.WriteLine($"[Warning] {message}");
        public static void LogError(object message) => Console.WriteLine($"[Error] {message}");
    }

    public static class Application
    {
        public static string dataPath => "/Assets";
        public static bool isPlaying => false;
        public static bool isEditor => true;
    }
}
