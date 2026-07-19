# 连接型经济体与地缘经济碎片化的隐性成本

## 摘要

本项目研究 connector economies 在 geoeconomic fragmentation 中的福利价值。核心问题不是简单证明哪些国家“替代了中国”，也不是重复已有文献对 trade reallocation 和 trade rerouting 的识别。更合适的定位是：在中美贸易摩擦、Section 301 关税、friend-shoring 和 nearshoring 背景下，越南、墨西哥等第三方经济体是否通过贸易绕行、跨国生产调整和投入产出网络缓解了碎片化造成的福利损失。主模型应定位为 intensive-margin welfare accounting：它量化 trade-cost shock 和 MP-cost shock 的福利含义；新企业进入、新工厂公告和 greenfield FDI 项目应作为模型外 extensive-margin evidence，用来验证叙事并约束 `hgamma` 情景，而不是被说成 Du-Wang 模型的内生结果。福利结果应明确写成 A/B/C 情景区间：Scenario A 是 trade-only connector 下界，Scenario B 是 incumbent MP-intensive 基准，Scenario C 是由 total FDI 和生产侧扩张证据约束的 total MP-adjustment upper-bound proxy。

## 一、项目现在应该如何定位

这个项目不能再被写成一篇单纯的 connector-country 事实论文。Schulze and Xin (2025) 已经系统区分了 trade reallocation 和 trade rerouting，并且对亚洲样本中的越南给出了比较强的生产侧证据。因此，本文的主贡献应从“识别 connector economies”转向“计算 connector economies 的 welfare value”。

更具体地说，本文应回答三个问题。第一，当直接中美或 bloc-to-bloc 联系变贵时，第三国贸易通道能缓解多少福利损失。第二，如果已有或模型中已表示的跨国生产能够向墨西哥、越南等 connector locations 做 intensive reallocation，福利缓冲是否明显大于单纯贸易绕行。第三，如果把 BEA、Mexico FDI、AMNE 和 production-side expansion 记录到的 total MP adjustment 作为 Scenario C 上界输入，福利区间会扩大多少。fDi Markets 只保留为以后可选的项目级扩展。

因此，论文的合同应写得很清楚：经验部分负责验证事实、选择国家、约束 shock size；结构模型负责 welfare accounting；当前用 BEA MNE、AMNE、FDI、就业、投资和 value added 证据支持 nearshoring 叙事，并约束 Scenario B 和 Scenario C 的 `hgamma` 区间，但不等同于模型内生 entry。fDi Markets 本批不处理。

## 二、文献地图和本文位置

这个项目的文献基础不能只写成“IMF-CEPR 报告和 Schulze and Xin”。那样会显得项目只是跟随近期政策讨论，而没有清楚说明结构模型和 MP margin 的理论来源。更合理的文献地图应分成四层。

第一层是 fragmentation 和 connector facts 文献。IMF-CEPR 的 geoeconomic fragmentation 报告和 Freund、Mattoo、Mulabdic、Ruta 关于中美关税后贸易变化的章节提供了背景事实：美国从中国进口下降，同时越南、墨西哥、加拿大、印度、韩国、台湾地区等经济体在部分产品中扩大对美国出口，并且一些出口增长国家仍然增加从中国进口中间品。Schulze and Xin (2025) 是最直接的 empirical benchmark，因为它已经区分了 trade reallocation 与 trade rerouting，并使用 trade data、value-added measures、greenfield FDI evidence 和 synthetic control 研究亚洲 connector economies。

第二层是 quantitative trade / GVC welfare 文献。Du and Wang (2022) 是当前 reference 代码的直接来源，提供多国、多部门、trade、multinational production 和 input-output linkages 的一般均衡 welfare decomposition。Bonadio-Huo-Levchenko-Pandalai-Nayar 这一类 BHLP global supply-chain framework 是另一个重要参照：它更适合从全球供应链和投入产出网络角度做 shock propagation 和 welfare counterfactual。如果未来要放弃 Du-Wang 的 sufficient-statistics 结构，可以参考这条线重新搭建更简洁的 trade + IO + MP 层。

第三层是 multinational production margin 文献。Ramondo and Rodriguez-Clare 类型模型把 MP cost 作为 iceberg cost 进入生产和销售成本，适合解释既有 MP links 上的生产强度调整。Tintelnot (2017) 则是 fixed-cost foreign investment / export-platform 结构，更适合解释企业是否进入某个国家、是否开设 affiliate、是否形成新的 plant location。这个区分直接决定本项目能不能用 Du-Wang：Du-Wang 的 `hgamma` 属于前者，不属于 Tintelnot 式 fixed-cost entry。

第四层是 nearshoring 和 extensive-margin evidence。当前证据层由 BEA U.S. MNE Activity、OECD Analytical AMNE、Mexico FDI、USITC USMCA rules-of-origin reports 和 production-side statistics 构成。它们应该回答“墨西哥是否出现外资企业活动、就业、投资或 value added 扩张”，但这些事实应放在模型外 evidence section，而不是被塞进 Du-Wang 模型作为内生 entry。fDi Markets 如以后单独处理，只作为项目级补充。

## 三、核心研究问题

本文的主问题是：connector economies 在多大程度上缓解 geoeconomic fragmentation 的福利成本，这种缓解分别来自 trade rerouting、MP intensive reallocation、total MP-adjustment upper-bound proxy 和 IO propagation 的哪一部分。

这里至少要区分三种机制。第一，trade rerouting：美国或欧盟从中国进口下降，但从墨西哥、越南或其他第三国进口上升，同时第三国从中国或东亚进口相关中间品上升。第二，MP nearshoring：已有或模型中已表示的 multinational-production links 上，企业把更多生产强度配置到 connector locations，表现为 `hgamma` 下降或保持低成本。第三，extensive-margin entry：企业新进入墨西哥或新设工厂，这一点 Du-Wang 不能内生解释。当前只能用 BEA、AMNE、FDI 和生产侧数据在模型外提供间接验证，并作为 Scenario C 上界校准依据；fDi Markets 以后如单独处理，可增加项目级证据。

如果只研究第一种机制，论文会接近贸易绕行事实；如果能同时量化第二种机制，才有结构福利贡献；如果把第三种机制作为 Scenario C 的上界输入，则 reduced-form evidence 不再只是旁证，而是直接约束福利区间。必须注意：这仍然不是 fixed-cost entry model；如果要把第三种机制做成模型核心，就必须转向 Tintelnot-style fixed-cost entry model，工作量和数据要求都会明显上升。

## 四、国家、部门和叙事边界

核心国家应是越南和墨西哥。越南是文献 benchmark：Schulze and Xin (2025) 已经给出较强的亚洲样本证据，因此它适合作为 sanity check，而不是本文的主要新增事实。墨西哥是本文更有潜力的 North America extension：Section 301、USMCA、汽车和电子产业链、美国 MNE activity 与 Mexico FDI 已经构成更贴近 nearshoring 叙事的公开数据案例；fDi Markets 项目公告只保留为以后可选补充。

加拿大可以作为 North American connector 或 rules-of-origin 对照，但不应与墨西哥混为一类。印度、土耳其、波兰、摩洛哥、印尼、韩国、台湾地区等可以作为扩展或对照样本，但要按机制区分：有些更像 China-plus-one 替代生产，有些更像区域平台，有些是高技术中间品供应者，不一定都是同一种 connector。

优先部门应包括汽车及零部件、电子和计算机、机械设备、医疗器械，以及与 Section 301 暴露高度相关的中间品和资本品。行业选择不能只看出口增长，还要看第三国从中国进口投入品、本地 value added、MNE activity、FDI、就业和投资是否同步变化。

## 五、主模型边界：Du-Wang 可以用，但只能这样用

当前 reference 文件夹中的 Du and Wang (2022) 复现包不是 connector-economy 论文，但它提供了可改造的第一版结构骨架：多国、多部门，包含 trade、multinational production 和 input-output linkages，并且有 welfare decomposition。

我核验后的结论是：Du-Wang 的 MP margin 是 iceberg MP cost，不是 Tintelnot-style fixed-cost entry。论文中的 `gamma_iell^j` 是企业从 origin country `i` 在 location `ell` 生产时承担的有效成本；代码中的 `hgamma` 直接进入 `eqm_update.m` 的相对成本项 `hxi_4d`，再影响 MP shares 和 sourcing shares。代码没有固定成本、entry threshold、affiliate count、plant-count decision 或 relocation entry block。

这意味着，Du-Wang 可以回答的是：在既有国家-部门 MP links 上，如果有效 MP cost 改变，生产份额、贸易份额、中间品价格和福利如何变化。它不能回答的是：中国企业、美国企业或其他 MNE 是否因为 Section 301 在墨西哥新设工厂。

推荐方案是使用 Du-Wang 作为第一版结构模型，同时在模型外增加 extensive-margin evidence section，并把这些 evidence 直接服务于 A/B/C 情景校准。这样论文可以保持诚实边界：模型做 intensive-margin welfare accounting，当前用 BEA、AMNE、FDI 和生产侧数据检验 affiliate expansion 并设定 `hgamma` 情景；fDi Markets 以后如单独处理，只作为项目级补充。Scenario C 应写成 total MP-adjustment upper-bound proxy，不能写成 entry-margin welfare estimate。

第一组福利反事实应使用三个 connector scenarios。Scenario A 是 trade-only connector lower bound：connector 相关 `htau` 保持开放或下降，MP margin 设为 `hgamma = 1`，只允许贸易绕行，给出 connector welfare value 的下界。

Scenario B 是 incumbent MP-intensive baseline：用 AMNE、BEA MNE、ownership / affiliate activity moments 反推或约束 connector 相关 `hgamma`，衡量已有 MP links 上的 intensive production reallocation。这是本文第一版的基准情景。

Scenario C 是 total MP-adjustment upper-bound proxy：当前用 total FDI inflow、affiliate expansion 和 production-side expansion 约束更强的 `hgamma` 调整，让观测到的总生产扩张进入福利核算，但不声称模型内生 fixed-cost entry。fDi Markets 保留为以后单独加入的项目级证据，本批不处理。

B 到 C 的差值可以报告为 extensive-margin-related upper-bound increment，但不能写成识别出来的 entry-margin welfare contribution。

不推荐第一版直接转向 Tintelnot-style fixed-cost entry model，除非论文核心改成“企业为什么进入墨西哥”。那条路线更完整，但需要企业或项目层面的 entry 数据、固定成本识别、plant location choice 和更复杂的 counterfactual 结构。

## 六、数据策略和可得性

当前公开数据条件已经可以支持第一版结构福利论文的数据准备和 scenario-bound 设计。数据层应按功能分工，而不是混在一起；fDi Markets 不计入本批已完成资产。

1. OECD ICIO / Extended ICIO：免费，直接下载。它提供 IO、gross output、value added、final demand 和中间投入结构。Extended ICIO 对 China 和 Mexico 的 ownership / firm-type 拆分对本项目很有价值。限制是最新年份到 2022，不能覆盖完整 2023 nearshoring 高峰。

2. OECD Analytical AMNE / MNE-GVC：免费，直接下载。当前本地 2026 release 构建的可用交集覆盖 2008-2023，bilateral output 原始覆盖到 2024。这是 Scenario B `hgamma` ownership moments 的核心来源。需要注意：employment 不可得，parent-level value added、exports 和 imports 是按 affiliate-output share 分配的，不是直接报告的 bilateral cells。

3. BEA U.S. MNE Activity：公开免费，但部分国家-行业单元可能 suppressed。我们已经核实 Mexico x Transportation equipment 在 2020-2022 年核心指标没有 `(D)` suppression。下一步要检查 electronics/computers 和 medical devices。

4. fDi Markets：当前批次明确不处理，也没有下载或变量构造。以后如单独开启，可作为 greenfield project-level extensive-margin evidence；公告仍不等于实际投产，必须和 BEA、Mexico FDI、value added、employment、investment 交叉验证。

5. BACI：免费，直接下载。它提供 HS6 产品层面的双边年度贸易数据，适合构造 connector ranking、rerouting measure、Section 301 exposure 和行业层面的 `htau` shock。限制是没有 ownership 或 firm-level 信息，需要 HS-to-sector concordance。

6. Mexico Secretaria de Economia / DataMexico FDI：免费政府数据。它可以追踪 2021-2024 年墨西哥按来源国和行业拆分的 FDI flows。限制是 flow data，不是 affiliate output、value added 或 plant-level activity。

7. Section 301 tariff data：免费公开。USTR lists、USITC HTS 和相关整理数据可以把 2018-2019 年美国对华关税冲击映射到 HS 产品，再聚合到本项目行业。这是 `htau` 情景最干净的政策冲击来源。

8. USITC USMCA automotive rules-of-origin reports：免费法定报告。它对汽车部门很重要，因为 rules-of-origin compliance 可以帮助区分真实区域生产整合和 shallow assembly / rerouting。具体比例和表格必须在正式引用前复核。

## 七、第一阶段应交付什么

第一阶段不是跑完整结构模型，而是建立一组可以支撑模型的 facts 和 moments。

第一，literature benchmark table：明确 Schulze and Xin (2025) 已经做了什么，本文不重复什么，本文新增什么。

第二，connector ranking table：用 BACI 和 Section 301 暴露，在产品和行业层面识别哪些国家同时表现出对美国出口上升、从中国进口中间品上升和受冲击产品重叠。

第三，North America extension figure：重点看 Mexico 和 Canada 是否在亚洲样本之外表现出 connector 机制，尤其是汽车、电子、机械和医疗器械。

第四，extensive-margin evidence table：当前用 BEA MNE、OECD AMNE、Mexico FDI、就业、投资和 value added 证据，单独列出 affiliate activity 和生产侧扩张。这个表是模型外验证，不是 Du-Wang 的内生结果；fDi Markets 本批不进入该表。

第五，structural moment table：把贸易、value added、FDI 和 affiliate activity 事实转化为 Scenario A/B/C 中 `htau` 与 `hgamma` 的情景依据。

第六，小型 MATLAB-ready sample：验证新数据能否进入 reference 模型接口，再决定是否迁移 `eqm_iter.m`、`eqm_update.m`、`wel_decomp.m` 和相关函数。

## 八、能否达到 JIE 要求

可以，但前提是论文边界要诚实，并且模型和证据要对应。JIE 读者不会接受“用一个没有 entry margin 的模型解释新工厂进入”。但他们可以接受一个清楚的结构福利核算：模型量化给定 connector access 和 MP-cost scenarios 下的 welfare effects；模型外证据证明这些 scenarios 有现实依据。

本文最有潜力的贡献不是“第一次证明 nearshoring 存在”，而是把 connector economies 的作用分解为 trade-only rerouting、incumbent MP intensive reallocation、total MP-adjustment upper-bound proxy 和 IO propagation，并给出一个可以比较 direct fragmentation、Scenario A、Scenario B 和 Scenario C 的 welfare-bound matrix。

如果生产侧证据弱，论文应把相应国家写成 Scenario A: trade-only connector lower bound。如果 AMNE / BEA MNE 支持已有 MP links 上的生产强度调整，才可以设定 Scenario B。如果 BEA、Mexico FDI、AMNE 和生产侧数据共同支持墨西哥相关行业扩张，才可以设定 Scenario C。即使如此，也应说是 `hgamma` upper-bound proxy，而不是模型内生的新企业进入。fDi Markets 不属于当前判定条件。

## 九、近期下一步

第一，先建立 HS6/HTS10、OECD sectors、BEA industries 和 Mexico SCIAN 的统一 concordance，再用现有 BACI、Census、AMNE、BEA 和 Mexico FDI 构造 connector ranking 与 production-side validation。fDi Markets 暂不处理。

第二，建立 literature benchmark table，把 Schulze and Xin (2025)、Du and Wang (2022)、Ramondo and Rodriguez-Clare、Tintelnot (2017)、Bonadio-Huo-Levchenko-Pandalai-Nayar 这一组文献的作用分清楚：哪些是事实 benchmark，哪些是模型骨架，哪些是替代模型路线。

第三，只复现模型需要的最低限度事实：connector ranking、value-added moments、越南 sanity check 和 Mexico / North America extension。

第四，检查 BEA 中 Mexico x electronics/computers 和 Mexico x medical devices 是否存在 suppression，并下载 OECD ICIO Extended、OECD Analytical AMNE、BACI、Section 301 tariff files、Mexico FDI 和 USITC USMCA auto report。

第五，建立 extensive-margin evidence table 和 structural moment table，把每个 moment 明确分配到 Scenario A、Scenario B 或 Scenario C，再构造小型 MATLAB-ready sample。只有这些输入清楚后，才迁移完整 model core。

## References

1. Du, Xiayi, and Zi Wang. 2022. “Multinationals, Global Value Chains, and the Welfare Impacts of Economic Sanctions.” Economics Letters. 本项目第一版结构模型和 welfare decomposition 的直接来源。

2. Ramondo, Natalia, and Andres Rodriguez-Clare. 2013. “Trade, Multinational Production, and the Gains from Openness.” Journal of Political Economy. 用来理解 iceberg MP cost 和跨国生产份额调整的理论来源。

3. Tintelnot, Felix. 2017. “Global Production with Export Platforms.” Quarterly Journal of Economics. 用来界定 fixed-cost foreign investment / affiliate entry 模型；如果论文核心改成新企业进入，需要转向这条路线。

4. Bonadio, Barthélémy, Zhen Huo, Andrei A. Levchenko, and Nitya Pandalai-Nayar. 2021. “Global Supply Chains in the Pandemic.” Journal of International Economics. 作为 BHLP-style global supply-chain / IO counterfactual 框架的参照；若放弃 Du-Wang，可从这条线重构更简洁的 trade + IO + MP 模型。

5. Schulze, Tatjana, and Weining Xin. 2025. “Demystifying Trade Patterns in a Fragmenting World.” IMF Working Paper WP/25/129. 本项目最直接的 empirical benchmark；本文不应重复其 trade reallocation / rerouting 识别，而应转向 welfare accounting 和 Mexico / North America extension。

6. Freund, Caroline, Aaditya Mattoo, Alen Mulabdic, and Michele Ruta. IMF-CEPR geoeconomic fragmentation chapter on U.S.-China tariffs and connector economies. 用来提供中美关税后美国进口份额变化、第三国出口增长和 hidden dependence 的背景事实。

7. International Monetary Fund and CEPR. Geoeconomic Fragmentation: The Economic Risks from a Fractured World Economy. 用作政策背景和 fragmentation 叙事来源，不应替代本文自己的结构模型贡献。

8. Bown, Chad P., and related PIIE / USTR / USITC Section 301 tariff files. 用作产品层面关税冲击和 `htau` 情景的数据基础。

9. OECD ICIO, OECD Analytical AMNE / MNE-GVC, BEA U.S. MNE Activity, CEPII BACI, fDi Markets, Mexico Secretaria de Economia / DataMexico FDI, and USITC USMCA automotive rules-of-origin reports. 这些是数据和校准来源；正式论文中应按实际下载版本、年份覆盖和表格编号逐一引用。
