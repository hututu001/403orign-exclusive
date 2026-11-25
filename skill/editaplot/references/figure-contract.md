# Publication-informed Origin figure contract

Define this contract before choosing a renderer.

```text
Core conclusion:
Evidence role: discovery | comparison | mechanism | validation | robustness | composition | relationship
Audience/output:
Data unit and sample definition:
Primary comparison:
Required axes and units:
Series/color semantics:
Statistics and error definition:
Allowed display transforms:
Editable outputs:
Reviewer risk:
```

## Evidence rules

- Write one conclusion containing an action or relationship, not a topic label.
- Give each chart or panel one unique evidentiary job.
- Prefer the fewest views needed to support the conclusion.
- Keep the primary evidence visually dominant; make controls and context quieter.
- If no conclusion is provided, state a provisional one and ask for confirmation before final styling.

## Visual rules for Origin

- Use a white background, Arial, restrained semantic colors, and no decorative grid by default.
- Keep related conditions in one color family and reserve strong accents for the primary comparison.
- Choose a stable palette ID before rendering when color is user-selectable. Record its exact HEX
  values, allowed mode, group limit, and accessibility warnings in the plan. If the group count
  exceeds the safe limit, retain the verified default or add independently readable marker/line/hatch
  encoding rather than cycling invisible pale colors.
- Ask for explicit visual preferences independently of any reference image. The user may request
  exact series colors, physical line widths, fill transparency, page/aspect ratio, and legend
  visibility, frame, or position. A direct user request outranks a conflicting reference token;
  classify every field as applied, retained template default, or rejected before rendering.
- Keep semantic mappings for XPS components, signed effects, diagnostic reference curves, confusion
  matrices, and heatmaps unless the user explicitly confirms an exact replacement and that override
  route has been independently verified and read back. A reference image alone cannot reassign them.
- Avoid rainbow maps, ornamental 3D, shadows, glossy bars, and unjustified smoothing.
- Use direct labels when stable and readable; otherwise keep an editable legend. Legend overlap is
  not a hard failure when the OPJU remains editable.
- Resolve page size, margins, font sizes, line widths, error widths, and symbol sizes together from
  chart type, data density, series count, and label length. General figures are adaptive; only an
  explicitly named fixed profile may retain a fixed page such as 22.31 cm × 16.82 cm.
- Write physical page size through the verified Origin unit conversion route and read it back. Do
  the same for text and line widths; a small on-screen preview is not evidence of correct typography.
- Never shrink Origin text merely to make dense data fit. Recommend another layout or split figure.
- Treat axis binding as a style reset boundary. After every `axis -ps ... T dataset`, reapply and
  read back the visible X/Y/Y2 label font, point size, and color.
- Verify `xb`/`yl`/`yr`, legends, and manual annotations as separate editable text objects. The X
  and Y tick-label font codes must match the registered profile; equal-looking PNG glyphs are not enough.
- General defaults are Arial, 20 pt axis titles, 17 pt tick labels, and 17 pt legends. Registered
  density-specific profiles may vary; grouped-box and percent-composition legends use 18 pt.
- Put a percent-composition legend in a reserved external page column when it cannot fit the data
  field. Grouped-box legends are borderless editable labels, not the framed system-template legend.
- Heatmaps reserve a detached right margin for the colorbar and verify both colorbar and cell-label fonts.
- Ordinary categorical heatmaps freeze sparse row text and source-row positions. Their visible Y labels
  are separate, borderless editable Origin page objects, not missing axes: the numeric Y scale and
  complete matrix remain intact. Right-align measured text with the frozen 0.20 cm default frame gap;
  never shrink type or edit PNG pixels to hide a collision. Confusion matrices keep their own axis contract.

For XPS, cosmetic requests never change the source table, column roles, high-to-low binding-energy
direction, component identity, or verified fill construction. Exact colors, widths, transparency,
safe page/aspect ratios, and legend options may be applied only by a selected XPS renderer that has
passed the corresponding Origin API, object-readback, four-export, and visual-QA gate. Otherwise the
plan records the verified default or an explicit rejection; it does not describe the whole XPS style
as immutably locked.

## Scientific integrity

- Record `n`, center statistic, spread/error definition, test, correction, and comparison when relevant.
- Do not calculate statistics from replicates unless the user requests and confirms the method.
- Do not remove observations, normalize, baseline-correct, smooth, fit, or derive peaks silently.
- Keep source columns in the editable Origin workbook; create helper columns only for declared display transforms.

## Medical multi-panel rules

- Use 2–9 panels and give each panel one unique evidence role; panel labels are deterministic A–I.
- Quantitative panels must come from a `verified` route with complete OPJU/PNG/PDF/TIF/readback and
  an explicit human visual-QA pass.
- Image panels must be local PNG/JPEG/TIFF files with user attestations for deidentification and
  burned-in text review, plus modality, plane, and display parameters. The planner does not infer
  that private health information is absent.
- When two or more quantitative panels reuse conditions, freeze one condition-to-color map. Do not
  share a legend until shared semantics are explicitly confirmed.
- The V1 composer is a hash-bound layout plan, not an image-processing tool or merged OPJU renderer.
  Preserve the individual editable Origin subprojects as the quantitative evidence of record.

## 个人项目 profile：n4-f-u-v1.2

适用于用户已确认的 N4-F-U 局部绘图定制，记录日期为 2026-11-25。当前 Skill 的
`.editaplot-local.json` 登记此 profile 后，匹配 `engine_home` 的新计划会自动采用它；
未登记配置或使用其它 engine 的项目继续使用原默认，不全局替换通用或固定 XPS profile。

### 继承方式与参数来源

本 profile 是所选 EditaPlot 模板上的**局部个性化定制**，不是另一套独立规范。
先采用所选模板的既有合同、默认参数与验收流程，再仅覆盖用户明确指定或确认的字段。
用户未指定、未考虑或尚未确认的字段继续继承该模板；无需让用户重新设计完整绘图规范。
模板中也未定义且会影响科学含义的事项，按既有数据确认流程处理。

以最新用户截图为准：Graph1页面属性→打印/尺寸中，Origin整页宽11.36、高7.932 in。
这是原生整页尺寸，不是Layer1绘图区，也不是另建的导出补白画布。PNG600 dpi、Arial Bold与
28/26/24 pt、参照整图示例且图例一般在图里，均为明确要求。采用项目已有inside模式，
Layer1继承该模板的百分比布局，不保留外置图例预留栏，不强制改变图层宽高或分类轴旋转。
300 dpi、24-bit Color、3 pt线宽、15 pt符号、刻度与图层几何来自历史工程实读。
历史实读值作为参考记录，不因列入参数表就自动升级为已确认的用户覆盖项。
300 dpi说明旧图保存的导出设置；用户后续明确选用600 dpi，新计划采用600 dpi。
每次应用沿用既有计划记录用户覆盖与模板继承，保留历史证据来源；不会因某字段未列出就丢弃
开源项目对字体、数据角色、图型、误差表达或质量检查的其余要求。

CLI已接入此局部覆盖的计划冻结、worker重放和读回验收；当前主机的原生渲染是否成功，
仍须以该次smoke、实际OPJU/导出、对象读回与目视检查为准，不能由文档或单元测试代替。

| 参数 | 个性化设置与历史参照 |
| --- | --- |
| 主要导出格式 | 用户指定PNG、600 dpi；24-bit Color仅为历史参照，未作为新覆盖字段。保留可编辑OPJU及所选路线的其它交付要求 |
| Origin整页尺寸 | 英寸（in）；宽11.36，高7.932；厘米模型为28.8544 × 20.14728 |
| 图例位置 | `inside`；一般位于图内数据空白区域，按整图效果选择合适位置 |
| Layer1绘图区 | 继承所选模板inside模式的页面百分比，与整页尺寸分开验收 |
| 坐标轴标题 | Arial，28 pt，加粗 |
| 坐标轴刻度数字 | Arial，26 pt，加粗 |
| 图例与图内文字 | Arial，24 pt，加粗；包括系列标签、说明及图内注释 |
| 常规数据线 | 原工程常见3 pt；历史参照 |
| 常规符号大小 | 原工程常见15 pt；依据原生 `get -z` 的points单位定义，历史参照 |
| 坐标轴框线 | 原工程常见3 pt；历史参照 |
| 底轴、左轴刻度 | 原工程常见主次向外、主刻度长8 pt、相邻主刻度间1个次刻度；历史参照 |
| 图层位置与尺寸 | 原工程页面百分比：左17.9%、上11.6%、宽68.19%、高71.79%；历史参照 |

字号指正常文字的明确字号；化学式上下标继续使用原生上下标语义。历史工程中局部
`\p109`、`\p127` 等字号覆盖需结合文本读取，不能只看基础字号就判断符合 24 或 28 pt。
分类轴等图型专用规则仍须与当前数据角色一致；任何例外应记录到该图的合同中。

PNG按确认的原生整页尺寸和600 dpi直接导出，11.36×600=6816、7.932×600=4759.2，
整数像素约6816 × 4759。没有额外等比适配、缩放、补白、重采样或裁剪步骤。
页面打印点及 `page.resx/resy`、整页尺寸、Layer1百分比和PNG DPI分别记录；页面分辨率
不能替代PNG导出分辨率。直接按原物理尺寸输出时，28/26/24 pt与PNG按600 dpi解释的物理
字号对应，仅有栅格化取整误差。正式验收读取实际PNG，不能用预览代替。

### 已接入的配置与执行范围

复用 `AdaptiveOriginStyle.personal_profile`、`ScientificDisplayPlan.figure_style`、
`scientific_visual.apply_personal_profile()`、`build_plan()`、现有renderer、`verify_utils`
和 `export_graph()`。个人覆盖单独冻结在 `figure_contract.personal_profile`，不混入XPS原有
`figure_contract.visual_style`；不另建平行配置、渲染脚本或验收体系。

本机配置的 `personal_profile` 仅含 `id` 和 `overrides`。原有10项加以下3项柱图局部覆盖，允许子集，
不填充缺项；未知字段直接报错。用户截图为英寸，项目沿用厘米模型，按精确2.54系数换算。

| `overrides` 字段 | 本机已确认值 |
| --- | --- |
| `page_width_cm` / `page_height_cm` | 28.8544 / 20.14728（整页11.36 × 7.932 in） |
| `font_family` | `Arial` |
| `axis_title_size_pt` | 28 |
| `tick_label_size_pt` | 26 |
| `legend_size_pt` / `annotation_size_pt` | 24 / 24 |
| `bold` | `true` |
| `png_dpi` | 600 |
| `legend_position` | `inside` |
| `bar_border` | `none`，柱体无描边，轴框继承模板 |
| `bar_fill` | `two_color_center`，同色系双色渐变，水平方向两侧深、中间浅 |
| `bar_fill_transparency_percent` | 10 |

柱体覆盖仅用于 `bar`、`horizontal_bar`、`stacked_bar`、`percent_stacked_bar`。
其它模板保留这些冻结请求作为来源记录，并在应用报告中列入 `not_applicable_fields`，
不改动其填充或透明度。旧计划不自动获得新字段。

配色规则：主色 `C` 完整继承模板已解析色板，浅色 `H=round(0.30*C+0.70*255)` 按RGB通道生成。
70%混白是实现同色系高光的确定性方法，不是把另一个色板写成用户要求，也不是70%透明度。
对每根柱子的水平归一化坐标 `u∈[0,1]`，高光权重 `w=1-|2u-1|`；
渐变为 `(1-w)*C+w*H`，左/右边缘用主色，中心用浅色，再以90%不透明度叠加背景。
横向条形图仍按用户指定的水平方向渐变。单系列条形图若模板逐点赋色，其浅色也逐点从对应主色生成。

Origin使用 `-pbc -4` 表示无描边，`-pfm 3` 表示双色，`-pfp 0` 表示无填充图案，
`-pfb` 为主色、`-pff` 为浅色。已实测主题树 `Pattern.Fill.GradDirection=9`
对应主色在两侧、浅色在中心；`8`相反。主题 `ShadingMode=2` 为零起始编号，
不能与LabTalk的一起始 `-pfm 3` 混淆。第二颜色透明度使用 `Fill.Auto=1` 跟随整体，
并将 `PtnBkColor2Trans` 写为10后读回。只读取命名标量属性，不枚举或反序列化颜色列表二进制节点。
样式写入、逐项读回、原生导出和保存重开均复用现有流程；方向数字须同时与图面上的明暗位置一致。

`plan` 默认使用 `--personal-profile auto`；单次保留模板默认可传 `--personal-profile none`。
XPS的 `--visual-style-json` 若另行明确 `page_size_cm`，按项目既有显式请求优先规则处理。
其它未覆盖参数，包括Layer1百分比、线宽、轴框、符号、主色板、刻度、图层位置、非柱图透明度、
数据处理和科学语义，继续继承所选模板或已经确认的既有外观请求。此profile不新增半填符号配色操作。

内部布局复用所选模板的inside模式，不预留外置图例栏。已查看用户原图`120_Graph1A.png`与
`148_Graph69.png`：都是紧凑矩形图区，图例位于数据空白区；不把图例固定在同一角落，也不
照搬历史图层百分比。修改整页尺寸不触发额外的数据层百分比重算，不强制45°分类
标签旋转或68%图层高度，也不采用历史68.19%的宽度。沿用既有图例定位、边框和边界验收；
有裁切或文字重叠时报告具体问题，不以缩小字号或改动数据、内部几何来冒充符合个人要求。

计划保存规范化的 `id`、`overrides`、`profile_hash` 和带输入/输出计划digest的 `report`。
worker仅重放冻结内容并核验哈希，不隐式重读本机配置；旧plan缺少此字段时不追加新默认。
安装更新保留相同engine的本机profile，显式 `personal_profile: null` 可持续禁用本机默认。
正式渲染仍交付OPJU/PNG/PDF/TIF及报告；“PNG主要输出”不删减原有交付和验收要求。

此前7.933英寸、外置图例或导出补白方案的试验保留为历史记录，不作为最新截图所确认的
7.932英寸整页加inside模式的验收通过记录；须重新执行、重开并核对整页、Layer1与PNG。

本机最新验证已覆盖 `test_outputs/personal-profile-20261125/` 中 `bar-page`、`line-page`、
`xps-page` 三例（Origin 2021 / 9.80）。三例PNG实读6816 × 4759、599.9988 dpi；原生对象
及独立重开读回符合28/26/24 pt Arial加粗，图形样式保持，OPJU未被重开检查修改，重导PNG逐像素一致。
页面打印点高度4759÷600=7.9316667 in，界面三位显示7.932；厘米模型设定20.14728与原生
打印点读回20.146433333在既有容差内。此证据仅覆盖三类代表图，不代表所有图型或原工程全部半填符号均已验证。

本轮只读源工程补读证据：`参数实读V1.1/Graph5_storage.json`、`Graph15_storage.json`、
`Graph1A_storage.json`、`Graph69_storage.json` 中 `XFTHEME_EXPGRAPH` 的 PNG 配置为
`DotsPerInch=300`、`BitsPerPixel=24-bit Color`；`type=10` 对应 `png`，`export=0` 对应
`Active Page`。这些值来自保存于工程的导出设置，不是从预览图或页面分辨率推断。相应
`*_theme.json` 的页面 `/Dimension/Width=11.36`、`/Dimension/Height=7.933`；导出树也记录
相同宽高。这是历史7.933读数；最新用户截图明确7.932，当前默认以截图为准。
未核实的枚举值继续保留原始证据，不据其编号猜测设置含义。

符号大小15 pt来自原工程 `get -z` 读数15及 [Origin官方Get符号选项](https://docs.originlab.com/labtalk/ref/get_options_for_symbols/)
对 `-z` 单位points（1/72英寸）的定义。原始 `SizeUnit=0` 同时保留为尚未解析的枚举证据；
15 pt的结论不依赖将该编码解释为Points。

### 2026-11-25 坐标轴默认补齐

用户明确指出重绘图未体现规范的坐标轴，现将该节轴线与刻度设为个人覆盖：黑色四侧框线3 pt，底/左主次刻度向外、主长8 pt，线性数值轴次刻度1个，上/右常规无刻度和数字；双Y保留原有右轴角色。主刻度粗细、次刻度长度和粗细均原生Auto。新增字段为`frame_line_width_pt`、`major_tick_length_pt`、`axis_color`、`tick_direction`、`numeric_minor_ticks`、`tick_details`、`axis_frame`，当前共20项。旧13项冻结计划保持旧外观。

`apply_personal_axes`复用现有profile应用/读回入口，四侧独立读回`thickness/color/ticklength/ticks`，向外LabTalk编码10、向内5；数值范围、步长、尺度类型与标签可见性保持。Auto通过`personal_axes.c`的GetFormat具名标量读取，原生缺失哨兵为-1.23456789e-300；LabTalk不存在的tickthickness/mticklength属性返回NaN，不能拿它充当Auto证据。仅以包含12个刻度细项的局部Tree写入，避免重放完整图层主题改变轴标题位置。

仅常规笛卡尔模板及XPS适用；专用轴语义的图型保留模板并列入not_applicable_fields。分类轴不新增中间次刻度，对数轴保留原有分隔。其它历史数据线3 pt、符号15 pt、轴范围及图层百分比仍仅作参考。

## 403orign专属项目默认

2026-11-25，用户明确要求把已确认格式作为个人发行版的开箱默认。沿用上文的 profile 模型和原生应用/验证流程，默认的持久来源改为仓库中 `runtime/personal-profile.json`（20 项）；不再依赖本机隐藏配置。此节取代前文“仅本机配置启用”的加载说明。

优先级由低到高：所选模板 → 项目默认 profile → 匹配引擎的可选本机局部 profile → 本次支持的明确参数。缺省字段始终继承模板，格式不改变数据含义。`--personal-profile none` 临时恢复模板；匹配引擎的本机 `personal_profile: null` 仍可禁用。新图在计划阶段冻结实际合并值和哈希，重画旧图不重新加载新默认。

| 字段 | 值 | 范围 |
|---|---|---|
| page_width_cm / page_height_cm | 28.8544 / 20.14728 | 原生整页尺寸 |
| png_dpi | 600 | 整页导出 |
| font_family / bold | Arial / true | 已支持的标题、刻度、图例、注释 |
| axis_title_size_pt / tick_label_size_pt | 28 / 26 | 轴标题 / 刻度标签 |
| legend_size_pt / annotation_size_pt | 24 / 24 | 图例 / 注释 |
| legend_position | inside | 复用模板图内模式 |
| frame_line_width_pt / axis_color / axis_frame | 3 / #000000 / four_sides | 适用的笛卡尔图 |
| major_tick_length_pt / tick_direction | 8 / out | 主刻度；底/左向外，上/右保留框线 |
| numeric_minor_ticks / tick_details | 1 / auto | 线性数值轴；分类和对数轴保持语义 |
| bar_border / bar_fill | none / two_color_center | 柱图相关四类模板 |
| bar_fill_transparency_percent | 10 | 90% 不透明；双色透明度联动 |

柱体仍使用所选模板色板。每通道高光色 `H = round(0.30 × C + 0.70 × 255)`，横向从两侧的原色到中部高光再到原色，形成二维圆柱明暗；不是增加第三个数据维度。Origin 2021 实测双色模式 2、方向 9，无边框颜色 -4、无图案 0；读取主次颜色、方向和两种透明度后再看导出图的两侧深/中央浅，不用方向名字猜测。

后续只把用户明确确认的长期格式加入现有字段或必要扩展。优先查看上游对应功能，未要求的线宽、误差线、符号形状、半填、图层位置、科学色义等继续继承模板。热图、极坐标等特殊结构按现有适用范围报告字段不适用。
