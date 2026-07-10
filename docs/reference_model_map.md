# Reference Model Map

The folder `reference/EL_replication/EL_replication` is the upstream replication package for Du and Wang, "Multinationals, global value chains, and the welfare impacts of economic sanctions." It is treated as read-only source material.

## Reuse Principle

The project should reuse the model architecture, not the Russia-specific scripts. General model functions can be migrated into `code/model_core/` later. Event-specific scripts should be used only as design references.

## Files To Reuse As Model Core

| Reference file | Future use | Notes |
|---|---|---|
| `eqm_iter.m` | Equilibrium solver loop | Reuse after replacing hard-coded paths with function inputs. |
| `eqm_update.m` | Equilibrium update equations | Core model equations; keep dimensional conventions explicit. |
| `wel_decomp.m` | Welfare decomposition | Reuse to report GFF, GFI, GOF, SEC, MS, and PT for new scenarios. |
| `impute_tri.m` | Imputation helper | Reuse only after validating new trade and MP shares. |

## Files To Treat As Data-Build References

| Reference file | Future use | Notes |
|---|---|---|
| `data_tomatlab.do` | Template for converting Stata data to MATLAB CSV inputs | New version should read current OECD/Comtrade/BACI data. |
| `cal_gravity.do` | Template for sector-level gravity calibration | New version must document data sources and fixed effects carefully. |
| `main_impute_triflows.m` | Template for building `X_4d` from trade and MP shares | Useful for dimension checks and data interface design. |
| `main_cab.m` | Baseline current-account adjustment template | Reuse only after new baseline inputs are validated. |

## Files To Use Only As Scenario Examples

| Reference file | Why not directly reuse |
|---|---|
| `main_cf_RUS_sanction.m` | Hard-codes Russia, China, and a specific sanction case. |
| `main_cf_RUS_sanction2.m` | Hard-codes the current-sanction country set. |
| `main_cf_RUS_sanction_notrade.m` | Trade-only Russia scenario; useful as a conceptual contrast only. |
| `main_cf_RUS_sanction_notrade2.m` | Trade-only current-sanction variant; not a general runner. |

## Required Refactor Before Model Migration

Before any MATLAB model code is copied into `code/model_core/`, the new project needs:

- country mapping table with stable IDs, ISO codes, and bloc membership;
- sector mapping table from trade products to ICIO/AMNE sectors;
- scenario configuration file defining blocked, connector, source, and destination countries;
- explicit Scenario A/B/C fields for trade-only lower bound, incumbent MP-intensive baseline, and total MP-adjustment upper-bound proxy;
- input validation that checks dimensions before solving the model;
- output naming rules that include data vintage and scenario name.

## Connector Scenario Bounds

The first connector-economy welfare matrix should compare direct fragmentation with three bounded connector scenarios:

| Scenario | Model object | Interpretation |
|---|---|---|
| Scenario A: trade-only connector lower bound | Connector-related `htau` remains open or improves; `hgamma = 1`. | Lower bound for connector value through gross trade rerouting only. |
| Scenario B: incumbent MP-intensive baseline | Connector-related `hgamma` is disciplined by AMNE, BEA MNE, or ownership/affiliate activity moments. | Preferred intensive-margin baseline across already represented MP links. |
| Scenario C: total MP-adjustment upper-bound proxy | Connector-related `hgamma` is disciplined by total FDI, fDi Markets project evidence, affiliate expansion, and production-side expansion. | Upper-bound proxy for total MP adjustment; not a structural fixed-cost entry model. |

The B-to-C gap can be reported as an extensive-margin-related upper-bound increment. It should not be labeled as identified entry-margin welfare because the reference model has no affiliate-entry or plant-entry block.

## Welfare Decomposition Interpretation

The reference decomposition should be preserved:

- `GFF`: gains from foreign final goods;
- `GFI`: gains from foreign intermediates;
- `GOF`: gains from offshoring / MP access;
- `SEC`: sectoral input-output linkage channel;
- `MS`: market size effect;
- `PT`: profit and tariff revenue channel.

For this project, the key reporting requirement is to decompose how much connector economies reduce direct fragmentation losses and how much welfare cost remains after accounting for indirect sourcing through connectors. Reports should separately show Scenario A trade-only mitigation, Scenario B incumbent MP-intensive reallocation, the Scenario C upper-bound increment, and the IO propagation channel.
