// Stub definitions for UnityEditor assemblies to allow offline C# compilation and automated verification
using System;
using UnityEngine;

namespace UnityEditor
{
    [AttributeUsage(AttributeTargets.Method, AllowMultiple = true)]
    public class MenuItem : Attribute
    {
        public string menuItem;
        public bool validate;
        public int priority;
        public MenuItem(string menuItem) { this.menuItem = menuItem; }
        public MenuItem(string menuItem, bool validate) { this.menuItem = menuItem; this.validate = validate; }
        public MenuItem(string menuItem, bool validate, int priority) { this.menuItem = menuItem; this.validate = validate; this.priority = priority; }
    }

    public class EditorWindow : ScriptableObject
    {
        public static T GetWindow<T>(string title = null, bool focus = true) where T : EditorWindow, new() => new T();
        public void Show() { }
        public void Repaint() { }
        public Vector2 minSize { get; set; }
        public Vector2 maxSize { get; set; }
        public string titleContent { get; set; }
    }

    public class ScriptableObject : UnityEngine.Object { }

    public static class EditorGUILayout
    {
        public static void BeginHorizontal(params GUILayoutOption[] options) { }
        public static void EndHorizontal() { }
        public static void BeginVertical(params GUILayoutOption[] options) { }
        public static void BeginVertical(GUIStyle style, params GUILayoutOption[] options) { }
        public static void EndVertical() { }
        public static Vector2 BeginScrollView(Vector2 scrollPosition, params GUILayoutOption[] options) => scrollPosition;
        public static void EndScrollView() { }
        public static void LabelField(string label, params GUILayoutOption[] options) { }
        public static void LabelField(string label, GUIStyle style, params GUILayoutOption[] options) { }
        public static void LabelField(string label, string text, params GUILayoutOption[] options) { }
        public static void LabelField(string label, string text, GUIStyle style, params GUILayoutOption[] options) { }
        public static string TextField(string label, string text, params GUILayoutOption[] options) => text;
        public static string TextField(string text, params GUILayoutOption[] options) => text;
        public static int IntField(string label, int value, params GUILayoutOption[] options) => value;
        public static float FloatField(string label, float value, params GUILayoutOption[] options) => value;
        public static bool Toggle(string label, bool value, params GUILayoutOption[] options) => value;
        public static Enum EnumPopup(string label, Enum selected, params GUILayoutOption[] options) => selected;
        public static void HelpBox(string message, MessageType type) { }
        public static void Space(float width = 6f) { }
    }

    public static class EditorGUI
    {
        public static int indentLevel { get; set; } = 0;
        public static void DrawRect(Rect rect, Color color) { }
    }

    public static class GUILayout
    {
        public static bool Button(string text, params GUILayoutOption[] options) => false;
        public static bool Button(string text, GUIStyle style, params GUILayoutOption[] options) => false;
        public static void Label(string text, params GUILayoutOption[] options) { }
        public static void Label(string text, GUIStyle style, params GUILayoutOption[] options) { }
        public static void Space(float pixels) { }
        public static GUILayoutOption Width(float width) => new GUILayoutOption();
        public static GUILayoutOption Height(float height) => new GUILayoutOption();
        public static GUILayoutOption ExpandWidth(bool expand) => new GUILayoutOption();
        public static GUILayoutOption ExpandHeight(bool expand) => new GUILayoutOption();
    }

    public class GUILayoutOption { }

    public class GUIStyle
    {
        public GUIStyle() { }
        public GUIStyle(GUIStyle other) { }
        public int fontSize { get; set; }
        public FontStyle fontStyle { get; set; }
        public TextAnchor alignment { get; set; }
        public Color normalTextColor { get; set; }
        public RectOffset margin { get; set; } = new RectOffset();
        public RectOffset padding { get; set; } = new RectOffset();
        public bool wordWrap { get; set; }
    }

    public enum FontStyle { Normal, Bold, Italic, BoldAndItalic }
    public enum TextAnchor { UpperLeft, UpperCenter, UpperRight, MiddleLeft, MiddleCenter, MiddleRight, LowerLeft, LowerCenter, LowerRight }

    public class RectOffset
    {
        public int left, right, top, bottom;
        public RectOffset() { }
        public RectOffset(int left, int right, int top, int bottom) { this.left = left; this.right = right; this.top = top; this.bottom = bottom; }
    }

    public struct Rect
    {
        public float x, y, width, height;
        public Rect(float x, float y, float width, float height) { this.x = x; this.y = y; this.width = width; this.height = height; }
    }

    public static class EditorStyles
    {
        public static GUIStyle boldLabel => new GUIStyle { fontStyle = FontStyle.Bold };
        public static GUIStyle label => new GUIStyle();
        public static GUIStyle miniButton => new GUIStyle();
        public static GUIStyle toolbarButton => new GUIStyle();
        public static GUIStyle helpBox => new GUIStyle();
        public static GUIStyle centeredGreyMiniLabel => new GUIStyle();
    }

    public enum MessageType { None, Info, Warning, Error }

    public static class EditorUtility
    {
        public static string OpenFilePanel(string title, string directory, string extension) => "";
        public static string OpenFolderPanel(string title, string folder, string defaultName) => "";
        public static bool DisplayDialog(string title, string message, string ok, string cancel = "") => true;
        public static void DisplayProgressBar(string title, string info, float progress) { }
        public static void ClearProgressBar() { }
        public static void SetDirty(UnityEngine.Object target) { }
    }

    public static class AssetDatabase
    {
        public static string[] FindAssets(string filter) => new string[0];
        public static string[] FindAssets(string filter, string[] searchInFolders) => new string[0];
        public static string GUIDToAssetPath(string guid) => "";
        public static T LoadAssetAtPath<T>(string assetPath) where T : UnityEngine.Object => null;
        public static void SaveAssets() { }
        public static void Refresh() { }
    }

    public static class PrefabUtility
    {
        public static UnityEngine.Object InstantiatePrefab(UnityEngine.Object assetComponentOrGameObject) => UnityEngine.Object.Instantiate(assetComponentOrGameObject);
        public static UnityEngine.Object InstantiatePrefab(UnityEngine.Object assetComponentOrGameObject, Transform parent) => UnityEngine.Object.Instantiate(assetComponentOrGameObject, parent);
    }

    public static class Undo
    {
        public static void RegisterCreatedObjectUndo(UnityEngine.Object objectToUndo, string name) { }
        public static void DestroyObjectImmediate(UnityEngine.Object objectToDestroy) { UnityEngine.Object.DestroyImmediate(objectToDestroy); }
        public static void RecordObject(UnityEngine.Object objectToUndo, string name) { }
    }

    public static class Selection
    {
        public static UnityEngine.GameObject activeGameObject { get; set; }
        public static UnityEngine.Object[] objects { get; set; } = new UnityEngine.Object[0];
    }

    public class SceneView : ScriptableObject
    {
        public static SceneView lastActiveSceneView => null;
        public void FrameSelected() { }
        public static void Frame(Bounds bounds, bool instant) { }
    }

    public static class GUI
    {
        public static Color backgroundColor { get; set; } = Color.white;
        public static Color color { get; set; } = Color.white;
    }
}
