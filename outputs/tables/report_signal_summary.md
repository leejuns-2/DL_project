# Report-to-Market Signal Summary

## 쉬운 설명

PDF 보고서를 그냥 요약하는 데서 끝내지 않고, 보고서 안에서 에너지 전환과 관련된 근거 문단을 찾고,
범용 Transformer 임베딩 모델로 사람이 정의한 예시 문장과 PDF 문단의 의미 유사도를 비교해 산업별 점수로 바꿨습니다.
쉽게 말해, 긴 보고서를 읽어서 `재생에너지`, `화석연료 압력`, `전력망`, `기후 리스크` 점수표로 만든 것입니다.

## Foundation Model 연결

- 범용 임베딩 모델: `sentence-transformers/all-MiniLM-L6-v2`
- 역할: PDF 문단과 예시 문장의 의미를 벡터로 변환
- Example-based semantic scoring: 모델 파라미터를 추가 학습하지 않고, 사람이 만든 예시 문장과 새 보고서 문단의 의미 유사도를 계산
- Downstream task: 보고서 점수를 ETF/기업 주가 수익률과 연결

## Report Signals

| report_id           | title                                            | date       | issuer     |   renewable_opportunity |   fossil_pressure |   grid_infrastructure |   climate_risk |   transition_signal | asset_hint                  |
|:--------------------|:-------------------------------------------------|:-----------|:-----------|------------------------:|------------------:|----------------------:|---------------:|--------------------:|:----------------------------|
| exxon_acs_2023      | ExxonMobil Advancing Climate Solutions 2023      | 2023-04-04 | ExxonMobil |                  0.6768 |            0.7295 |                0.668  |         0.7053 |              1.3206 | XLE/XOM transition pressure |
| iea_weo_2023        | IEA World Energy Outlook 2023                    | 2023-10-24 | IEA        |                  0.7321 |            0.7094 |                0.7115 |         0.7043 |              1.4385 | ICLN/NEE                    |
| iea_oil_gas_nz_2023 | IEA Oil and Gas Industry in Net Zero Transitions | 2023-11-23 | IEA        |                  0.707  |            0.7361 |                0.6925 |         0.6821 |              1.3455 | XLE/XOM transition pressure |
| iea_renewables_2023 | IEA Renewables 2023                              | 2024-01-11 | IEA        |                  0.7319 |            0.6826 |                0.7172 |         0.686  |              1.4525 | ICLN/NEE                    |
| eaton_annual_2023   | Eaton Annual Report 2023                         | 2024-02-23 | Eaton      |                  0.6682 |            0.6401 |                0.6902 |         0.6545 |              1.3728 | ETN                         |

## Extractive Summaries

### Eaton Annual Report 2023

- Date: `2024-02-23`
- Simple explanation: 이 보고서는 에너지 전환을 시장 신호로 바꾸기 위해 읽은 자료입니다. 재생에너지 점수는 0.67, 전력망/전기화 점수는 0.69, 화석연료 압력 점수는 0.64입니다. 쉽게 말해, 보고서 내용이 어떤 산업에 더 좋은 뉴스인지 숫자로 바꾼 것입니다.
- Evidence summary: The effects of climate change, including weather disruptions and regulatory/market reactions, create uncertainties that could negatively impact our business. | We make products for the data center, utility, industrial, commercial, machine building, residential, aerospace and mobility markets. | As the world’s demand for electricity grows, so does the need for Eaton’s innovative technology and solutions. | 5 EATON 2023 Annual Report carbon emissions generated at all our plants and granted the first certification to our facility in Riom, France. | Regulatory reactions to climate change may pose more stringent obligations on Eaton’s operations and change customer demands.

### ExxonMobil Advancing Climate Solutions 2023

- Date: `2023-04-04`
- Simple explanation: 이 보고서는 에너지 전환을 시장 신호로 바꾸기 위해 읽은 자료입니다. 재생에너지 점수는 0.68, 전력망/전기화 점수는 0.67, 화석연료 압력 점수는 0.73입니다. 쉽게 말해, 보고서 내용이 어떤 산업에 더 좋은 뉴스인지 숫자로 바꾼 것입니다.
- Evidence summary: Each of these processes includes the critical elements of leadership, people, risk identification and management, and continuous improvement. | ExxonMobil | Advancing Climate Solutions | 2023 Progress Report 52 10 Section 10 | Our risk management approach Once facilities are in operation, we maintain disaster preparedness, response, and business continuity plans. | In recent history, the world has seen an increase in energy use per capita as living conditions in the developing world have improved, more than offsetting efficiency trends in the developed world. | Natural gas is projected to have less demand reduction due to its many advantages, including lower greenhouse gas emissions. | 92 Scope 1 (direct emissions) include emissions from exported power and heat.

### IEA Oil and Gas Industry in Net Zero Transitions

- Date: `2023-11-23`
- Simple explanation: 이 보고서는 에너지 전환을 시장 신호로 바꾸기 위해 읽은 자료입니다. 재생에너지 점수는 0.71, 전력망/전기화 점수는 0.69, 화석연료 압력 점수는 0.74입니다. 쉽게 말해, 보고서 내용이 어떤 산업에 더 좋은 뉴스인지 숫자로 바꾼 것입니다.
- Evidence summary: Reducing methane emissions is the single most important measure that companies can take to reduce their scope 1 and 2 emissions intensity. | But full electrification would lead to even greater efficiency improvements. | The best prospects for growth are in the United States, Southeast Asia and Africa, given their untapped potential and growing electricity demand. | No companies have to date made specific pledges on this. | Will the oil and gas industry be part of the solution?

### IEA Renewables 2023

- Date: `2024-01-11`
- Simple explanation: 이 보고서는 에너지 전환을 시장 신호로 바꾸기 위해 읽은 자료입니다. 재생에너지 점수는 0.73, 전력망/전기화 점수는 0.72, 화석연료 압력 점수는 0.68입니다. 쉽게 말해, 보고서 내용이 어떤 산업에 더 좋은 뉴스인지 숫자로 바꾼 것입니다.
- Evidence summary: Until now, programmes to increase renewable capacity have found creative solutions to work around the region’s low amount of transmission and distribution infrastructure, such as the French Development Agency’s proposal to develop solar PV installations along existing transmissio | Spain data from Red Eléctrica de Espana. | Internationally, establishing globally recognised GHG emissions intensity values can help improve trade, allowing regions with more low-carbon feedstocks to sell fuel to regions without. | The International Maritime Organization is also considering introducing a low-carbon fuel standard and a carbon price for international marine fuels, but details have not been published so it is not considered in our forecast. | Most PV manufacturing capacity expansion to 2028 is expected to take place in China, ranging from 85% for modules to 95% for polysilicon.

### IEA World Energy Outlook 2023

- Date: `2023-10-24`
- Simple explanation: 이 보고서는 에너지 전환을 시장 신호로 바꾸기 위해 읽은 자료입니다. 재생에너지 점수는 0.73, 전력망/전기화 점수는 0.71, 화석연료 압력 점수는 0.71입니다. 쉽게 말해, 보고서 내용이 어떤 산업에 더 좋은 뉴스인지 숫자로 바꾼 것입니다.
- Evidence summary: The growing impacts of global warming make this all the more important, as an increasing amount of energy infrastructure that was built for a cooler, calmer climate is no longer reliable or resilient enough as temperatures rise and weather events become more extreme. | Chapter 1 | Overview and key findings 37 1 Figure 1.10 ⊳ Global solar module manufacturing and solar PV capacity additions in the STEPS, 2010-2030 IEA. | Expanded, modernised and cybersecure transmission and distribution grids are critical to electricity security in a world where the share of solar PV and wind in electricity generation is rising rapidly. | Solar is leading the charge: solar PV capacity, including both large utility-scale and small distributed systems, accounts for two-thirds of the 2023 estimated increase in global renewable capacity. | Copper, rare earth elements, silicon and various battery metals, notably lithium, are critical minerals for electrification.

## Downstream Link to Stock Returns

| report_id           |   transition_signal |   forward_4w_ET_SPREAD |   forward_4w_ICLN |   forward_4w_XLE |   forward_4w_ETN |
|:--------------------|--------------------:|-----------------------:|------------------:|-----------------:|-----------------:|
| exxon_acs_2023      |              1.3206 |                -0.0821 |           -0.0541 |           0.0278 |          -0.0246 |
| iea_weo_2023        |              1.4385 |                 0.1211 |            0.0519 |          -0.0617 |           0.179  |
| iea_oil_gas_nz_2023 |              1.3455 |                 0.1003 |            0.0936 |          -0.0046 |           0.0422 |
| iea_renewables_2023 |              1.4525 |                -0.0439 |           -0.0554 |          -0.0137 |           0.15   |
| eaton_annual_2023   |              1.3728 |                -0.0801 |            0.0007 |           0.0836 |           0.1146 |
