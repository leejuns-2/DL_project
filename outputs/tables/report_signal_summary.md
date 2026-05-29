# Report-to-Market Signal Summary

## 쉬운 설명

PDF 보고서를 그냥 요약하는 데서 끝내지 않고, 보고서 안에서 에너지 전환과 관련된 근거 문단을 찾고,
범용 Transformer 임베딩 모델로 사람이 정의한 예시 문장과 PDF 문단의 의미 유사도를 비교해 산업별 점수로 바꿨습니다.
쉽게 말해, 긴 보고서를 읽어서 `재생에너지`, `화석연료 압력`, `전력망`, `기후 리스크` 점수표로 만든 것입니다.

## Pre-trained Transformer Embedding 연결

- 범용 임베딩 모델: `sentence-transformers/all-MiniLM-L6-v2`
- 역할: PDF 문단과 예시 문장의 의미를 벡터로 변환
- Few-shot classifier: MiniLM 임베딩은 고정하고, 사람이 만든 소수 라벨 예시로 Logistic Regression 분류 헤드를 학습
- Downstream task: 보고서 점수를 ETF/기업 주가 수익률과 연결

## Report Signals

| report_id           | title                                            | date       | issuer     | scoring_method                              |   renewable_opportunity |   fossil_pressure |   grid_infrastructure |   climate_risk |   transition_signal | asset_hint                  |
|:--------------------|:-------------------------------------------------|:-----------|:-----------|:--------------------------------------------|------------------------:|------------------:|----------------------:|---------------:|--------------------:|:----------------------------|
| exxon_acs_2023      | ExxonMobil Advancing Climate Solutions 2023      | 2023-04-04 | ExxonMobil | few_shot_logistic_head_on_minilm_embeddings |                  0.5814 |            0.8667 |                0      |         1      |              0.7147 | Climate risk                |
| iea_weo_2023        | IEA World Energy Outlook 2023                    | 2023-10-24 | IEA        | few_shot_logistic_head_on_minilm_embeddings |                  1      |            0.0232 |                0      |         0.0016 |              0.9784 | ICLN/NEE                    |
| iea_oil_gas_nz_2023 | IEA Oil and Gas Industry in Net Zero Transitions | 2023-11-23 | IEA        | few_shot_logistic_head_on_minilm_embeddings |                  0.6496 |            1      |                0.4485 |         0      |              0.0981 | XLE/XOM transition pressure |
| iea_renewables_2023 | IEA Renewables 2023                              | 2024-01-11 | IEA        | few_shot_logistic_head_on_minilm_embeddings |                  1      |            0.499  |                0.7184 |         0      |              1.2194 | ICLN/NEE                    |
| eaton_annual_2023   | Eaton Annual Report 2023                         | 2024-02-23 | Eaton      | few_shot_logistic_head_on_minilm_embeddings |                  0.5181 |            0      |                1      |         0.6798 |              2.1978 | ETN                         |

## Extractive Summaries

### Eaton Annual Report 2023

- Date: `2024-02-23`
- Simple explanation: 이 보고서는 에너지 전환을 시장 신호로 바꾸기 위해 읽은 자료입니다. 재생에너지 점수는 0.52, 전력망/전기화 점수는 1.00, 화석연료 압력 점수는 0.00입니다. 쉽게 말해, 보고서 내용이 어떤 산업에 더 좋은 뉴스인지 숫자로 바꾼 것입니다.
- Evidence summary: The effects of climate change, including weather disruptions and regulatory/market reactions, create uncertainties that could negatively impact our business. | We make products for the data center, utility, industrial, commercial, machine building, residential, aerospace and mobility markets. | As the world’s demand for electricity grows, so does the need for Eaton’s innovative technology and solutions. | 5 EATON 2023 Annual Report carbon emissions generated at all our plants and granted the first certification to our facility in Riom, France. | Regulatory reactions to climate change may pose more stringent obligations on Eaton’s operations and change customer demands.

### ExxonMobil Advancing Climate Solutions 2023

- Date: `2023-04-04`
- Simple explanation: 이 보고서는 에너지 전환을 시장 신호로 바꾸기 위해 읽은 자료입니다. 재생에너지 점수는 0.58, 전력망/전기화 점수는 0.00, 화석연료 압력 점수는 0.87입니다. 쉽게 말해, 보고서 내용이 어떤 산업에 더 좋은 뉴스인지 숫자로 바꾼 것입니다.
- Evidence summary: Each of these processes includes the critical elements of leadership, people, risk identification and management, and continuous improvement. | ExxonMobil | Advancing Climate Solutions | 2023 Progress Report 52 10 Section 10 | Our risk management approach Once facilities are in operation, we maintain disaster preparedness, response, and business continuity plans. | In recent history, the world has seen an increase in energy use per capita as living conditions in the developing world have improved, more than offsetting efficiency trends in the developed world. | Natural gas is projected to have less demand reduction due to its many advantages, including lower greenhouse gas emissions. | 92 Scope 1 (direct emissions) include emissions from exported power and heat.

### IEA Oil and Gas Industry in Net Zero Transitions

- Date: `2023-11-23`
- Simple explanation: 이 보고서는 에너지 전환을 시장 신호로 바꾸기 위해 읽은 자료입니다. 재생에너지 점수는 0.65, 전력망/전기화 점수는 0.45, 화석연료 압력 점수는 1.00입니다. 쉽게 말해, 보고서 내용이 어떤 산업에 더 좋은 뉴스인지 숫자로 바꾼 것입니다.
- Evidence summary: Reducing methane emissions is the single most important measure that companies can take to reduce their scope 1 and 2 emissions intensity. | But full electrification would lead to even greater efficiency improvements. | The best prospects for growth are in the United States, Southeast Asia and Africa, given their untapped potential and growing electricity demand. | No companies have to date made specific pledges on this. | Will the oil and gas industry be part of the solution?

### IEA Renewables 2023

- Date: `2024-01-11`
- Simple explanation: 이 보고서는 에너지 전환을 시장 신호로 바꾸기 위해 읽은 자료입니다. 재생에너지 점수는 1.00, 전력망/전기화 점수는 0.72, 화석연료 압력 점수는 0.50입니다. 쉽게 말해, 보고서 내용이 어떤 산업에 더 좋은 뉴스인지 숫자로 바꾼 것입니다.
- Evidence summary: Until now, programmes to increase renewable capacity have found creative solutions to work around the region’s low amount of transmission and distribution infrastructure, such as the French Development Agency’s proposal to develop solar PV installations along existing transmissio | Spain data from Red Eléctrica de Espana. | Internationally, establishing globally recognised GHG emissions intensity values can help improve trade, allowing regions with more low-carbon feedstocks to sell fuel to regions without. | The International Maritime Organization is also considering introducing a low-carbon fuel standard and a carbon price for international marine fuels, but details have not been published so it is not considered in our forecast. | Most PV manufacturing capacity expansion to 2028 is expected to take place in China, ranging from 85% for modules to 95% for polysilicon.

### IEA World Energy Outlook 2023

- Date: `2023-10-24`
- Simple explanation: 이 보고서는 에너지 전환을 시장 신호로 바꾸기 위해 읽은 자료입니다. 재생에너지 점수는 1.00, 전력망/전기화 점수는 0.00, 화석연료 압력 점수는 0.02입니다. 쉽게 말해, 보고서 내용이 어떤 산업에 더 좋은 뉴스인지 숫자로 바꾼 것입니다.
- Evidence summary: The growing impacts of global warming make this all the more important, as an increasing amount of energy infrastructure that was built for a cooler, calmer climate is no longer reliable or resilient enough as temperatures rise and weather events become more extreme. | Chapter 1 | Overview and key findings 37 1 Figure 1.10 ⊳ Global solar module manufacturing and solar PV capacity additions in the STEPS, 2010-2030 IEA. | Expanded, modernised and cybersecure transmission and distribution grids are critical to electricity security in a world where the share of solar PV and wind in electricity generation is rising rapidly. | Solar is leading the charge: solar PV capacity, including both large utility-scale and small distributed systems, accounts for two-thirds of the 2023 estimated increase in global renewable capacity. | Copper, rare earth elements, silicon and various battery metals, notably lithium, are critical minerals for electrification.

## Downstream Link to Stock Returns

| report_id           |   transition_signal |   forward_4w_ET_SPREAD |   forward_4w_ICLN |   forward_4w_XLE |   forward_4w_ETN |
|:--------------------|--------------------:|-----------------------:|------------------:|-----------------:|-----------------:|
| exxon_acs_2023      |              0.7147 |                -0.0821 |           -0.0541 |           0.0278 |          -0.0246 |
| iea_weo_2023        |              0.9784 |                 0.1211 |            0.0519 |          -0.0617 |           0.179  |
| iea_oil_gas_nz_2023 |              0.0981 |                 0.1003 |            0.0936 |          -0.0046 |           0.0422 |
| iea_renewables_2023 |              1.2194 |                -0.0439 |           -0.0554 |          -0.0137 |           0.15   |
| eaton_annual_2023   |              2.1978 |                -0.0801 |            0.0007 |           0.0836 |           0.1146 |