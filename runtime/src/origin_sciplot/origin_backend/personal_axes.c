#include <Origin.h>
#pragma labtalk(2)

// Named scalar access to native tick details. OriginExt layer.GetTheme omits
// axes, and LabTalk's undocumented tickthickness/mticklength return missing.
void ep_tick_read(TreeNode& node, string prefix)
{
    LT_set_var(prefix + "minor_length", node.MinorLength.dVal == -1.23456789e-300);
    LT_set_var(prefix + "major_width", node.TicksWidth.dVal == -1.23456789e-300);
    LT_set_var(prefix + "minor_width", node.MinorWidth.dVal == -1.23456789e-300);
}

void editaplot_personal_tick_details()
{
    double apply = 0;
    LT_get_var("__ep_axis_apply", &apply);
    char graph_name[256];
    LT_get_str("__ep_axis_graph", graph_name, 256);
    double layer_index = 0;
    LT_get_var("__ep_axis_layer", &layer_index);
    GraphPage gp(graph_name);
    GraphLayer gl = gp.Layers((int)layer_index);
    LT_set_var("__ep_axis_details_ok", 0);
    if (!gl) return;
    if (apply) {
        // Apply only these twelve scalars. Replaying the whole layer format
        // also resets axis-title attachment/offsets on Origin 2021.
        Tree tr;
        tr.Root.Axes.X.Ticks.BottomTicks.MinorLength.dVal = -1.23456789e-300;
        tr.Root.Axes.X.Ticks.BottomTicks.TicksWidth.dVal = -1.23456789e-300;
        tr.Root.Axes.X.Ticks.BottomTicks.MinorWidth.dVal = -1.23456789e-300;
        tr.Root.Axes.X.Ticks.TopTicks.MinorLength.dVal = -1.23456789e-300;
        tr.Root.Axes.X.Ticks.TopTicks.TicksWidth.dVal = -1.23456789e-300;
        tr.Root.Axes.X.Ticks.TopTicks.MinorWidth.dVal = -1.23456789e-300;
        tr.Root.Axes.Y.Ticks.LeftTicks.MinorLength.dVal = -1.23456789e-300;
        tr.Root.Axes.Y.Ticks.LeftTicks.TicksWidth.dVal = -1.23456789e-300;
        tr.Root.Axes.Y.Ticks.LeftTicks.MinorWidth.dVal = -1.23456789e-300;
        tr.Root.Axes.Y.Ticks.RightTicks.MinorLength.dVal = -1.23456789e-300;
        tr.Root.Axes.Y.Ticks.RightTicks.TicksWidth.dVal = -1.23456789e-300;
        tr.Root.Axes.Y.Ticks.RightTicks.MinorWidth.dVal = -1.23456789e-300;
        if (gl.UpdateThemeIDs(tr.Root)) return;
        gl.ApplyFormat(tr, TRUE, TRUE);
    }
    // Re-read independently rather than reporting the requested tree.
    Tree actual;
    actual = gl.GetFormat(FPB_ALL, FOB_ALL, TRUE, TRUE);
    ep_tick_read(actual.Root.Axes.X.Ticks.BottomTicks, "__ep_axis_0_");
    ep_tick_read(actual.Root.Axes.X.Ticks.TopTicks, "__ep_axis_1_");
    ep_tick_read(actual.Root.Axes.Y.Ticks.LeftTicks, "__ep_axis_2_");
    ep_tick_read(actual.Root.Axes.Y.Ticks.RightTicks, "__ep_axis_3_");
    LT_set_var("__ep_axis_details_ok", 1);
}
