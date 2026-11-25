# Origin delivery verification

Do not report success from a rendered preview or PNG alone.

## Live connection smoke

Doctor discovery is never connection evidence. Before the first render in an environment, or after
its Python, Origin, or Automation target changes, run the real smoke through an EditaPlot-owned
isolated instance. The smoke must complete:

- Automation activation and initialization;
- actual Origin version and executable-path readback;
- a minimal editable workbook and graph;
- non-empty OPJU, PNG, PDF, and TIF outputs in an isolated test directory;
- minimum axis-object readback.

A smoke failure is a staged technical failure, not a reason to ask the user to open Origin manually.
A successful smoke proves the current connection and minimum core capabilities only; it does not
prove that every template is available. Apply the selected template's capability decision next.

## Mandatory files

- non-empty editable `result.opju`;
- non-empty `result.png`;
- non-empty `result.pdf` with usable text/fonts;
- non-empty `result.tif`;
- validation and provenance reports;
- `origin_verify_report.json` with page/graph/axis/style readback.

## Programmatic checks

- Confirm every reported artifact resolves inside the run output directory.
- Confirm the input copy hash matches the inspected source hash.
- Confirm `data_understanding.status` is `confirmed`, its source hash matches the render source,
  every source column is classified exactly once, no item remains `uncertain`, and every visible
  element binds only primary/secondary source data or an explicitly approved allow-listed helper.
- For a reference-driven plan, confirm the image/spec hashes, essential mark bindings, applied and
  rejected style tokens, and that no reference pixels, OCR text, code, source values, author marks,
  logos, or watermarks entered the plan or output folder.
- Confirm page dimensions and registered layer geometry. The geometry report must include
  `geometry_readback_source`, `layer_unit`, the canonical left/top/width/height values, the
  correctly mapped `layer -x` values, raw bridge values when available, and
  `bridge_geometry_consistent`. Accept a stale bridge only when the two native LabTalk paths agree
  and still match the registered contract; otherwise fail closed.
- Read physical page centimetres from documented printer dots divided by the actual positive
  `page.resx/resy`, then multiply by 2.54. Record COM page dimensions as diagnostics; never substitute
  a guessed DPI or widen the page-size tolerance to hide a mismatch. A failed physical-size check
  may report only its check ID, measured value, expected value and tolerance.
- Confirm required axes, titles, label tables, scale direction, tick visibility, text sizes and font codes,
  plot widths, frame widths, and special plot labels where applicable.
- Confirm the X and Y tick-label font codes are identical to the registered profile after any
  dataset-backed label binding. Confirm Y-axis typography independently; do not infer it from X.
- Confirm legends, direct labels, notes, heatmap cell text, and colorbar labels have their own
  point-size and font readback whenever those objects exist.
- For ordinary heatmaps, verify the page row labels against frozen source indices/text after export:
  no duplicate automatic Y labels; literal text mode (`link=0`), correct font/size, attachment and rotation; no clipping,
  vertical overlap or invasion of the data frame. Read actual bounding boxes and the positive
  physical frame gap, not only a label count. For renderer regression, repeat these checks after
  independently reopening the saved OPJU and verify every matrix value and row/column order.
- Treat missing readback as a rendering failure even if exports exist.
- For Rietveld figures, confirm Observed/Calculated/optional Background/Difference source bindings,
  that Publication `Diff` uses identity display values, and that every phase-tick plot reads its X
  range from the original sparse Phase column while only its Y lane is a helper. Confirm the
  documented point-sized vertical-bar symbol kind `10` when phase ticks exist. Symbol `58` is a
  full-height X-position line and must not be accepted as a Rietveld reflection tick.

## Human visual checks

- Open the PNG or TIF and inspect axes, titles, X/Y font consistency, labels, colors, line weights,
  colorbar separation, clipping, and unexpected objects.
- Check that scientific direction and transforms match the figure contract.
- Check that the figure remains readable at its intended physical size.
- Allow legend overlap only when the legend remains editable and no data meaning is lost.
- Record visual QA as pending until a human or Codex with image inspection has reviewed an export.

## 自动个人 profile 的验收

当冻结计划含 `figure_contract.personal_profile` 时，除原有检查外，核对以下证据；没有该字段
的旧计划按原有合同验收，不因本机后来启用个人配置而改变判定。

- 冻结的 `id`、`overrides`、`profile_hash` 与应用报告hash一致，报告的输出digest与最终计划
  digest一致。worker只重放冻结配置；page_width_cm/page_height_cm属于原生整页，不能误写为Layer1尺寸。
- `origin_verify_report.json.personal_profile` 是实际Origin对象读回，必须与冻结id/hash/覆盖项
  匹配，且 `passed`、`plot_styles_preserved` 为true。分别记录物理页面、轴及文字对象；无轴图型
  可有空的轴列表，不能为了验收新增模板原本没有的轴。
- `personal_profile_application` 与独立的 `personal_profile_report.json` 记录计划应用过程；
  它们不能覆盖或冒充实际 `personal_profile` 读回。worker缺少匹配的实际读回时不能报告成功。
- 整页厘米对照确认的28.8544 × 20.14728 cm（11.36 × 7.932 in）或另行明确的XPS页面请求，
  沿用 `PAGE_SIZE_TOLERANCE_CM` 的0.03 cm容差；Layer1百分比另与inside模板比较。检查Arial字体、轴标题28 pt、
  刻度26 pt、图例与图内文字24 pt以及加粗；上下标保留科学文本语义。未指定属性继承模板，
  不把历史3 pt线宽、15 pt符号或历史图层位置当成新默认。
- 明确的 `legend_position: inside` 必须进入所选模板的现有inside模式；不保留外置图例栏。
  参照用户Graph1A、Graph69的完整图面，核对图例位于图区合适空白处、数据与文字清楚；
  核对图例边界、附着方式和边框。Layer1百分比与类别旋转继承该模式，不额外强制层宽、层高、45°或68%。
- PNG按冻结的原生整页尺寸及 `png_dpi` 直接导出，理论6816 × 4759.2，整数像素约6816 × 4759。
  不增加等比适配、缩放、补白或裁剪；按600 dpi解释的PNG物理字号应对应原生28/26/24 pt。
  `verify`再次读取实际PNG文件，检查格式、整页像素与DPI元数据（600，容差0.02），并记录整数取整结果。
  JSON中的 `verified: true` 不能替代文件检查；旧工程300 dpi和24-bit记录仅属历史证据。
- 保存OPJU后，沿现有独立重开检查读取这些文字和页面属性、确认数据及图形样式保持，并检查
  重导PNG。未执行的原生渲染、独立重开或目视检查必须分别标为未验证。

上述自动计划、重放及检查入口已经实现；这不构成当前Origin主机或所有模板已经通过原生运行
验收的声明。按实际运行记录报告通过项和剩余项，不能将单元测试通过写成Origin交付完成。
此前7.933英寸、外置图例或补白导出的试验不算最新7.932英寸原生整页inside路线的验收证据。
本机最新三例为 `bar-page`、`line-page`、`xps-page`，见 `test_outputs/personal-profile-20261125/`；
每例 `origin_verify_report.json` 和 `saved-project-verification.json` 均已通过，后者记录
`project_unchanged: true`、`plot_styles_preserved: true`、`reexport_pixel_identical: true`。
该范围不外推到所有模板或原工程未重验的半填系列；最终报告继续逐项说明未覆盖场景。

## 半填符号、颜色与保存后的验收

柱图启用个人双色渐变时，`origin_plot_state.colors` 逐系列核对 `-pfb`主色、
`-pbc=-4`无描边、主题树第二颜色、双色模式、方向9、图案0、整体透明度10以及
第二色自动跟随。`personal_profile.plot_styles[].column_fill` 保存相同原生标量，
用于字体应用前后和独立重开后的保持性比较；单系列条形图同时核对逐点主色与第二色。
保存重开需要再次运行原生样式校验，核对原工作表值、误差棒、图例动态样本与文字，
重导PNG并比较像素；只验证主色不构成渐变通过。目视检查应见两侧深、中间浅、
无柱体描边，坐标轴边框按所选模板保留。

2026-11-25本机Origin 2021 / 9.80的新柱图实例：
`examples/gallery/bar_grouped_error_EditaPlot_20261125_210146/`。
使用项目自带三系列、五分类和已给SD的示例，主色沿模板解析为
`#59666F / #247B8B / #C66454`，浅色为`#CDD1D4 / #BDD7DC / #EED0CC`。
OPJU/PNG/PDF/TIF、原生逐项读回、独立只读重开、工作表原值与误差值、
动态图例样本、6816×4759 PNG / 599.9988 dpi均通过；重导PNG逐像素一致。
证据为该目录的`origin_verify_report.json`、`saved-project-verification.json`和
`verification-final.json`。这验证了当前主机的分组柱图实例，不能扩展为其它Origin版本
或所有条形/堆积图的实机验收声明。

半填符号或已有独立符号配色的图，复用现有 Origin 读回报告，逐系列分别记录并核对：

- 曲线颜色 `get -c`；
- 符号边色 `get -cse`；
- 符号填色 `get -csf`；
- 符号内部/半填方式 `get -kf`，同时保留形状 `get -k` 和尺寸的读回。

`-c` 符合系列色不代表边色、填色及半填方向也符合。不得为所有半填符号把 `-csf` 固定为白色，
也不得未经当前符号类型验证就把所有颜色字段设成同一值；应按所选形状、内部填充方式和用户要求，
确定有色部分及留白部分的实际属性映射。读取到跟随系列、自动或其它特殊代码时保留原值与语义，
不得伪装成已经确认的 RGB；必要时使用当前 Origin 的已验证解析路径确认最终颜色。

完成原生属性读回后，查看 Origin 导出的 PNG，逐项确认曲线色、符号有色部分、边线、形状、
半填方向和图例样本一致。图例应对应当前系列及其真实符号样式，不能仅核对文字、字号或颜色。

保存 OPJU 后，在独立的自有 Origin 实例中只读重开保存文件，重复这些属性与图例核对，并重新导出
PNG进行目视检查。复用现有会话所有权、源数据/hash、工作表和图页检查流程，不保存覆盖原工程，
不把保存前状态或仅有文件存在当作保存后验证。记录重开读回和重导图的路径及结果；未执行的项目
明确标为未验证，不能由单次 `-c` 检查推断通过。

### 坐标轴追加验收

20项个人profile应用时，`personal_profile.axis_styles`必须分别记录四侧轴线颜色与3 pt宽度、底/左向外编码10、主刻度8 pt、上/右常规刻度0、线性数值轴次刻度1，以及四侧三个细项的原生Auto。只读重开用`apply=False`重复检查；轴范围、步长、尺度及标签可见性保持，图形样式保持，PNG重导一致。分类轴和对数轴仍按已有语义处理，不把柱图实例外推为全部图型均已实测。

## 个人发行版默认加载验收

新增 checkout 必须在没有 `.editaplot-local.json` 时自动冻结仓库的20项默认；本机局部覆盖、单次 none、跨引擎隔离、旧计划重放均需保持各自语义。原模板回归使用显式隔离配置，另以 `test_project_profile_defaults.py` 验证真实仓库默认，不能用隔离测试代替默认加载验收。原生验收仍逐项写入读回并保存重开；发布不得包含本机配置、私人源数据或机器路径。
