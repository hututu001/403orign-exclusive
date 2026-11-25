<div align="center">
  <img src="runtime/src/origin_sciplot/resources/app_icon.png" width="64" alt="EditaPlot 图标">
  <h1>403orign专属</h1>
  <p><strong>把表格交给 Codex，把可编辑的科研图带回 Origin</strong></p>
  <p>理解数据 · 选择表达 · 定制样式 · 检查交付</p>
  <p>
    <img alt="Apache-2.0 开源" src="https://img.shields.io/badge/license-Apache--2.0-0f766e?style=flat-square">
    <img alt="Windows 10/11 x64" src="https://img.shields.io/badge/Windows-10%2F11%20x64-315b7d?style=flat-square">
    <img alt="Python 3.11–3.12" src="https://img.shields.io/badge/Python-3.11%E2%80%933.12-315b7d?style=flat-square">
    <a href="https://github.com/hututu001/403orign-exclusive"><img alt="GitHub Stars" src="https://img.shields.io/github/stars/hututu001/403orign-exclusive?style=social"></a>
  </p>
  <p><a href="#开始使用">三步开始</a> · <a href="docs/gallery.md">看图选模板</a> · <a href="#三种常用提问直接复制">复制提示词</a> · <a href="docs/quickstart.zh-CN.md">完整教程</a> · <a href="README.en.md">English</a></p>
</div>

这是基于 [EditaPlot](https://github.com/hang-jin/editaplot) 的个人发行版，由 hututu001 维护个人格式定制。你把表格和想表达的问题告诉 Codex，它会先说明每列的用途，等你确认后，再调用本机 Origin 绘图和检查结果。

它是一个 **Codex Skill，不是独立绘图软件**。你仍然可以在 Origin 中继续编辑曲线、坐标轴和图例；配色、线宽与版式也可以在已支持的范围内按你的需求调整。

**使用前提：Windows 10/11 x64 实体电脑 + Codex + 本机 Origin/OriginPro。** 日常使用不需要提前打开 Origin；Mac、Linux、WSL 和虚拟机暂不支持。

## 安装后默认就是我的格式

默认配置随仓库发布于 [`runtime/personal-profile.json`](runtime/personal-profile.json)，新图自动启用，无需复制本机隐藏配置，也无需每次重复格式要求。首次安装仍需本机已有 Origin，并运行 `setup` 和 `doctor`。

| 项目 | 默认值 |
|---|---|
| 页面 / PNG | 28.8544 × 20.14728 cm / 600 dpi |
| 字体 | Arial 加粗；轴标题 28 pt，刻度 26 pt，图例和注释 24 pt |
| 图例 | 图内，复用模板的布局机制 |
| 常规坐标轴 | 黑色四侧 3 pt；底/左刻度向外；主刻度 8 pt；线性数值轴 1 个次刻度；细节 Auto |
| 柱状图 | 无边框；模板原色 → 同色浅色 → 原色的横向中心渐变；10% 透明度 |
| 其它样式与能力 | 继续继承所选原模板；不自动覆盖色板、数据线、误差线、符号形状或半填 |

规则是 **模板默认 → 本项目确认的格式 → 可选本机局部覆盖 → 本次支持的明确参数**。坐标轴规则仅用于适用的笛卡尔图；分类/对数/极坐标、热图等保持其科学语义。旧方案重画时继续使用冻结值。临时恢复原模板可用 `--personal-profile none`。

改长期默认，只需编辑上述 JSON 中已支持的字段；已有 profile 的应用、预览、原生读回和保存重开流程继续复用。新需求先查上游现成能力，缺少时才在现有扩展点补充。详细参数、适用范围和原理见[现有绘图规范](skill/editaplot/references/figure-contract.md#403orign专属项目默认)。

当前 20 项个人样式已在本机 Origin 2021 分组柱图完成原生读回和保存重开，重导 PNG 像素一致。其它路线继承上游能力分级，不代表全部已在此主机实测。

## 先看看能画什么

<table>
  <tr>
    <td width="50%" align="center" valign="top">
      <a href="assets/gallery/xps-fit.png"><img src="assets/gallery/xps-fit.png" width="420" alt="真实 Origin XPS 原始谱与已提供分峰，合成教学数据"></a><br>
      <strong>XPS 原始谱与已提供分峰</strong><br>
      <sub>按实际列展示背景、包络和组分，不补造缺失峰。</sub>
    </td>
    <td width="50%" align="center" valign="top">
      <a href="assets/gallery/medical-grouped-box.png"><img src="assets/gallery/medical-grouped-box.png" width="420" alt="真实 Origin 分组箱线图与原始观测点，合成教学数据"></a><br>
      <strong>分组箱线与原始点</strong><br>
      <sub>同时看组间分布和每个观测，而不只看一根柱子。</sub>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center" valign="top">
      <a href="assets/gallery/shap-dashboard-blue-red.png"><img src="assets/gallery/shap-dashboard-blue-red.png" width="420" alt="真实 Origin SHAP 特征重要性、分组贡献环图与蜂群分栏，合成教学数据"></a><br>
      <strong>SHAP：重要性、贡献与蜂群</strong><br>
      <sub>使用上游已提供的逐样本 SHAP；绘图层不训练模型。</sub>
    </td>
    <td width="50%" align="center" valign="top">
      <a href="assets/gallery/heatmap-dense-30x30.png"><img src="assets/gallery/heatmap-dense-30x30.png" width="420" alt="真实 Origin 30乘30高密度热力图与独立色标，900个合成教学源值"></a><br>
      <strong>30 × 30 高密度热力图</strong><br>
      <sub>保留全部 900 个源值与行列顺序，不插值、不自动聚类。</sub>
    </td>
  </tr>
</table>

这些示例都用**合成教学数据，由真实 Origin 生成**，不代表实验或临床结论。点击图片可以看原图。

**[浏览全部 45 条绘图路线 →](docs/gallery.md)**　[荧光 / EEG 研究信号](docs/research_signals.md)　[English gallery](docs/gallery.en.md)

## 开始使用

### 1 / 安装：这段话交给 Codex

不会 GitHub 也没关系，把下面这段话复制给 Codex：

~~~text
请帮我安装最新 main 版 403orign专属（EditaPlot 个人版）：
仓库：https://github.com/hututu001/403orign-exclusive
请下载并保留完整仓库（包括 runtime），运行根目录 editaplot.cmd setup 和 doctor。
优先复用已有的 64 位 Python 3.11/3.12；需要安装 Python 时先问我。
不要安装或修改 Origin，不要修改注册表、DCOM，也不要申请管理员权限或控制鼠标。
完成后用中文告诉我环境是否就绪，再让我提供数据。
~~~

也可以[下载完整 ZIP](https://github.com/hututu001/403orign-exclusive/archive/refs/heads/main.zip)，完整解压后让 Codex 在该文件夹里安装。**不要只复制 <code>skill/editaplot</code> 子目录**，它需要仓库中的绘图引擎。

<details>
<summary>我会用 Git，直接给我安装命令</summary>

~~~powershell
git clone https://github.com/hututu001/403orign-exclusive.git
Set-Location 403orign-exclusive
.\editaplot.cmd setup
.\editaplot.cmd doctor
~~~

首次运行缺少兼容 Python 时，先按[安装指南](docs/installation.md)完成确认与配置。项目依赖只进入本项目环境，不修改全局 Python。

</details>

### 2 / 提供数据：说清楚想比较什么

在新的 Codex 对话中使用 <code>$editaplot</code>，附上 CSV、TXT、XLS 或 XLSX。可以先这样说：

~~~text
请用 $editaplot 看这份数据，先不要画图，也不要修改原文件。
请用中文说明每列用途，推荐最多三种合适的图，并告诉我还需要确认什么。
~~~

支持中文列名和中文路径。不确定该画哪种图，就让它先推荐；已经有目标，也可以直接说“分组箱线图”“XPS 多谱线对比”或“预计算 SHAP”。

不会整理列名？可以先打开[对应模板的数据样例](docs/gallery.md)，也可以让 Codex 解释现有表格与样例的差异。需要的辅助列只在内存或可编辑 Origin 工作簿中创建，原文件保持不变。

### 3 / 确认绘图：收下可继续编辑的结果

确认组别、单位、误差含义和要呈现的图形元素后，就可以继续说：

~~~text
按刚才确认的方案调用 Origin 绘图，导出可编辑 OPJU 和 PNG、PDF、TIF。
请检查数据映射、坐标轴、字体和导出后的视觉效果，最后简要告诉我输出位置与检查结果。
~~~

我会让 Skill 先完成本机绘图检查，再处理正式数据；不会补造原文件没有的测量值、分峰或误差。

正式结果默认集中保存在原始数据旁的新文件夹中：

~~~text
我的数据.csv
我的数据_EditaPlot_<时间>/
  render-plan.json
  result.opju
  result.png
  result.pdf
  result.tif
  ……反读与验证报告
~~~

想在 Origin 里接着改，就补一句“完成后保留可编辑窗口”。**有图片不等于已经完成**：正式交付还需要真实的 OPJU、其他导出格式以及数据和图形检查。完整过程见[中文教程](docs/quickstart.zh-CN.md)。

<details>
<summary>已经安装旧版，怎样更新？</summary>

让 Codex 检查本地改动、保留你的文件，再安全更新完整仓库并重新运行 <code>editaplot.cmd setup</code> 和 <code>doctor</code>。

当前安全运行时使用 Python 3.11/3.12 与 Pillow 13，新建环境优先 3.12；Python 3.10 不再承载当前依赖。旧项目环境和替换下来的 Skill 会保留为备份，不会悄悄退回旧依赖。旧方案若提示 <code>analysis_changed</code>，请重新理解、确认并生成方案，不要手改 JSON。

</details>

## 三种常用提问，直接复制

### 不确定该画什么

~~~text
请用 $editaplot 只读分析这份表格。我想比较不同组的差异，暂时没有确定图形。
请推荐最多三种表达方式，说明各自需要哪些列，等我确认后再绘图。
~~~

### 已经知道要画什么

~~~text
请用 $editaplot 画分组箱线图，并叠加原始观测点。
先确认分组、纵轴单位、每个观测的含义与样本量，不要自动添加显著性标记。
~~~

### 想参考一张图的风格

~~~text
请用 $editaplot 参考这张图的配色、线宽和布局，数据只用我提供的表格。
先列出当前模板能采用的样式、保留的默认值和无法实现的部分，等我确认后再画。
不要复制参考图的数据、结论、样品名或水印。
~~~

## 按你的数据选择模板

继承上游的 **45 条公开绘图路线**。同一路线可适配不同系列数、列名或已支持的显示模式，不需要为每种材料重新做一个模板。先看格式，再把自己的数据交给 Codex。

| 你的数据 | 常见表达 | 格式与示例 |
|---|---|---|
| 材料、光谱与电化学 | XPS、XRD/GSAS、PL/TRPL、UV–Vis/Tauc、FTIR、NMR、DSC、XAS、EIS、CV、LSV | [XPS 表格](runtime/templates/xps/data_template.csv) · [XRD 精修](runtime/templates/xrd/example_gsas_publication.csv) |
| 分组观测、误差与组成 | 柱/条形、原始点、箱线、小提琴、Raincloud、堆叠、百分比组成、森林图 | [分组箱线](runtime/templates/grouped_box/data_template.csv) · [带误差柱图](runtime/templates/bar/data_template.csv) |
| 医学与模型评估 | ROC、PR、校准、DCA、混淆矩阵、Bland–Altman、配对轨迹、预计算 SHAP | [分栏 SHAP 表格](runtime/templates/shap_dashboard/data_template.csv) · [图库](docs/gallery.md) |
| 荧光、EEG 与研究信号 | G–S 相量、共幅度多通道轨迹、时频矩阵、事件栅格 | [数据合同与用法](docs/research_signals.md) |
| 关系、流向与三维 | 散点、气泡、趋势、雷达、桑基、环形有向网络、具有真实第三轴的三维曲线 | [真实案例与数据](docs/gallery.md) |
| 分类矩阵 | 热力图与高密度矩阵；保留源值和顺序 | [输入格式](runtime/templates/heatmap/data_template.csv) |

XPS、GSAS、SHAP、寿命或带隙等有专门的科学边界。绘图层不会擅自做拟合、找峰、训练模型、重建影像或计算原始 EEG 的频谱；需要上游结果时会先说明。具体能力以对应模板和本机检查为准。

## 参考图和配色，也可以自己定

可以选择**模板默认、参考图建议、精确自定义**三种方式。你的明确选择优先；参考图只提供可采用的图形语法与风格，不复制它的数据、结论、样品名或水印。

例如在 XPS 中说：“Raw 用 <code>#173F5F</code>、线宽 <code>2.4 pt</code>、填充透明度 <code>38%</code>、画幅 <code>18 × 18 cm</code>，隐藏图例。”不同模板支持的调整项不同；Codex 会逐项说明采用、保留默认或拒绝，不把不支持的参数装成已经生效。

[查看中文配色卡](docs/palette-guide.md) · [参考图与精确样式规则](skill/editaplot/references/reference-figures.md)

## 使用前，知道这几件事就够了

| 项目 | 当前范围 |
|---|---|
| 系统 | Windows 10/11 x64 实体电脑；Mac、Linux、WSL、Wine/CrossOver、Parallels 和其他虚拟机暂不支持 |
| Python | 64 位 CPython 3.11 / 3.12；优先 3.12，安装器自动发现兼容版本 |
| Origin | 2021–2026b 是兼容目标；不是全部版本、全部模板组合都已验证 |
| 当前实机基线 | Python 3.12.14 + Pillow 13.0.0 + Origin 2024b（10.15.132），已完成 6 个代表案例回归；其他环境需先过 smoke 与模板能力检查 |
| 安装内容 | 完整仓库与项目隔离依赖；不捆绑、安装或修改 Origin |

**权限只给本次任务需要的范围**：读取仓库和选定数据；写入项目、当前用户的 <code>$HOME\.codex\skills\editaplot</code> 及数据所在文件夹；运行本地命令与专用 Origin 实例。下载和更新依赖时需要联网。

普通使用不需要管理员权限、鼠标控制、全盘写入或 DCOM、注册表、防火墙修改。遇到输出目录受保护时，只处理当前文件夹或明确指定另一个可写位置。

<details>
<summary>Codex 提示隔离上下文或权限不足时</summary>

让 Codex 为**原来的精确 Origin 命令**发起正式、受限的本地执行申请；只有获批才重跑，自动审查不保证批准，也不等于授权所有后续命令。不要把任务转到管理员 PowerShell，不要修改 DCOM/注册表或无限重试。

详细步骤和排队/耗时诊断见[安装与排障](docs/installation.md)。

</details>

**涉及隐私的数据先去标识化**，包括参考图里残留的姓名、编号等文字；我不承诺自动发现 PHI 或其他全部敏感信息。本地绘图程序不会主动把你的数据上传到网络，但交给 Codex 的文件仍受当前账号、组织和数据保留政策约束。详见[隐私说明](PRIVACY.md)。

<details>
<summary>常见疑问：卡住、排队、参考图没完全照着画？</summary>

- **安装或绘图一直不动**：先看最后停在哪一步，不要反复提交。环境与确认都已完成后，4–5 分钟是合理的本地流程参考，不是时限保证；无新进度却持续几十分钟时请让 Codex 按[分阶段排障](docs/installation.md#runtime-duration)检查。
- **同时开多个对话**：数据分析可以并行；同一 Windows 会话里的新版 EditaPlot 会让真正调用 Origin 的步骤排队，不要把等待提示当作失败。
- **参考图不能完全照搬**：参考图是视觉简报，不是任意图片一键复制。可支持的配色、线宽等可以定制，数据含义和已验证的绘图能力仍然是边界。
- **如何反馈问题**：告诉我 Windows / Origin 版本、最后的简短错误和能公开的最小样例即可。不要公开整份实验数据、病历、凭据或私人路径。

</details>

## 继续了解

| 我想做什么 | 从这里开始 |
|---|---|
| 看所有图形，找适合的数据格式 | [中文图库](docs/gallery.md) · [English gallery](docs/gallery.en.md) |
| 完整跑通第一张图 | [中文教程](docs/quickstart.zh-CN.md) · [English quick start](docs/quickstart.en.md) |
| 安装、升级、权限或运行慢 | [安装与排障](docs/installation.md) |
| 绘制荧光与研究信号 | [输入规范和使用说明](docs/research_signals.md) |
| 查 Origin 版本适配边界 | [2021–2026b 兼容说明](docs/origin-2021-2026-compatibility.md) |
| 了解源码、依赖与公开范围 | [发布边界](docs/release-boundaries.md) · [依赖清单](docs/dependency-inventory.md) |

## 来源与维护

本项目基于 [hang-jin/editaplot](https://github.com/hang-jin/editaplot)，保留原 Git 历史、[Apache-2.0 许可证](LICENSE)、[NOTICE](NOTICE) 和作者归属。个人版新增可移植默认 profile，以及既有个人样式的应用和验证；没有将原作者贡献改署为个人原创。

上游功能、教程和模板继续复用；`origin` 指向本个人仓库，`upstream` 可指向原仓库。同步前先检查差异，再运行已有回归和发布检查，不直接用上游文件覆盖个人默认。

[贡献说明](CONTRIBUTING.md) · [支持范围](SUPPORT.md) · [安全报告](SECURITY.md) · [隐私](PRIVACY.md)
