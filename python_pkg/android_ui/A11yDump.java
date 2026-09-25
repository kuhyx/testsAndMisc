package com.kuhy.a11ydump;

import android.accessibilityservice.AccessibilityServiceInfo;
import android.app.Activity;
import android.app.Instrumentation;
import android.app.UiAutomation;
import android.graphics.Rect;
import android.os.Bundle;
import android.os.SystemClock;
import android.util.SparseArray;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityWindowInfo;
import java.util.List;

/**
 * Dumps one display's accessibility tree as uiautomator-style XML.
 *
 * <p>Run: {@code am instrument -w -e display <id> com.kuhy.a11ydump/.A11yDump}. The
 * XML comes back on one line as the {@code xml} result key, in the same shape
 * {@code uiautomator dump} writes, so the Python side parses both with one
 * parser. Coordinates are the display's own, which is what {@code input -d}
 * expects.
 */
public final class A11yDump extends Instrumentation {
    private static final int ATTEMPTS = 15;
    private static final long RETRY_MS = 200;

    private Bundle arguments;

    @Override
    public void onCreate(Bundle args) {
        arguments = args;
        start();
    }

    @Override
    public void onStart() {
        Bundle out = new Bundle();
        try {
            int display = Integer.parseInt(arguments.getString("display", "0"));
            UiAutomation automation = getUiAutomation(
                    UiAutomation.FLAG_DONT_SUPPRESS_ACCESSIBILITY_SERVICES);
            AccessibilityServiceInfo info = automation.getServiceInfo();
            info.flags |= AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
                    | AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS
                    | AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS;
            automation.setServiceInfo(info);
            out.putString("xml", dump(automation, display));
            finish(Activity.RESULT_OK, out);
        } catch (Throwable t) {
            out.putString("error", String.valueOf(t));
            finish(Activity.RESULT_CANCELED, out);
        }
    }

    private static String dump(UiAutomation automation, int display) {
        // Windows appear a beat after the service info changes; an empty
        // list on the first read means "not yet", not "nothing there".
        List<AccessibilityWindowInfo> windows = null;
        for (int i = 0; i < ATTEMPTS; i++) {
            SparseArray<List<AccessibilityWindowInfo>> all =
                    automation.getWindowsOnAllDisplays();
            windows = all.get(display);
            if (windows != null && !windows.isEmpty()) break;
            SystemClock.sleep(RETRY_MS);
        }
        StringBuilder xml = new StringBuilder(
                "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
                        + "<hierarchy rotation=\"0\" display=\"" + display + "\">");
        if (windows != null) {
            // Bottom layer first, like uiautomator, so a dialog's nodes come
            // after (and so win over) the screen it covers.
            for (int w = windows.size() - 1; w >= 0; w--) {
                AccessibilityNodeInfo root = windows.get(w).getRoot();
                if (root != null) node(root, 0, xml);
            }
        }
        return xml.append("</hierarchy>").toString();
    }

    private static void node(AccessibilityNodeInfo n, int index, StringBuilder xml) {
        Rect r = new Rect();
        n.getBoundsInScreen(r);
        xml.append("<node index=\"").append(index).append('"');
        attr(xml, "text", n.getText());
        attr(xml, "resource-id", n.getViewIdResourceName());
        attr(xml, "class", n.getClassName());
        attr(xml, "package", n.getPackageName());
        attr(xml, "content-desc", n.getContentDescription());
        attr(xml, "hint", n.getHintText());
        flag(xml, "checkable", n.isCheckable());
        flag(xml, "checked", n.isChecked());
        flag(xml, "clickable", n.isClickable());
        flag(xml, "enabled", n.isEnabled());
        flag(xml, "focusable", n.isFocusable());
        flag(xml, "focused", n.isFocused());
        flag(xml, "scrollable", n.isScrollable());
        flag(xml, "password", n.isPassword());
        flag(xml, "selected", n.isSelected());
        xml.append(" bounds=\"[").append(r.left).append(',').append(r.top)
                .append("][").append(r.right).append(',').append(r.bottom)
                .append("]\">");
        for (int i = 0; i < n.getChildCount(); i++) {
            AccessibilityNodeInfo child = n.getChild(i);
            if (child != null) node(child, i, xml);
        }
        xml.append("</node>");
    }

    private static void flag(StringBuilder xml, String name, boolean value) {
        xml.append(' ').append(name).append("=\"").append(value).append('"');
    }

    private static void attr(StringBuilder xml, String name, CharSequence value) {
        xml.append(' ').append(name).append("=\"");
        if (value != null) {
            for (int i = 0; i < value.length(); i++) {
                char c = value.charAt(i);
                switch (c) {
                    case '&': xml.append("&amp;"); break;
                    case '<': xml.append("&lt;"); break;
                    case '>': xml.append("&gt;"); break;
                    case '"': xml.append("&quot;"); break;
                    // Newlines would split the one-line result `am` prints.
                    case '\n': xml.append("&#10;"); break;
                    case '\r': xml.append("&#13;"); break;
                    default: xml.append(c);
                }
            }
        }
        xml.append('"');
    }
}
