from __future__ import annotations

import csv
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "data" / "sample_pdfs"
REPORT_DIR = ROOT / "data" / "processed" / "reports"
CATALOG_PATH = REPORT_DIR / "validation_pdf_catalog.csv"
MANIFEST_PATH = REPORT_DIR / "sample_pdf_manifest.csv"


@dataclass(frozen=True)
class PdfSpec:
    report_id: str
    title: str
    date: str
    issuer: str
    filename: str
    expected_hint: str
    source: str


PDF_SPECS = [
    PdfSpec("irena_global_renewables_outlook_2020", "IRENA Global Renewables Outlook 2020", "2020-04-20", "IRENA", "IRENA_Global_Renewables_Outlook_2020.pdf", "ICLN/NEE", "https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2020/Apr/IRENA_Global_Renewables_Outlook_2020.pdf"),
    PdfSpec("irena_renewable_energy_statistics_2020", "IRENA Renewable Energy Statistics 2020", "2020-07-01", "IRENA", "IRENA_Renewable_Energy_Statistics_2020.pdf", "ICLN/NEE", "https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2020/Jul/IRENA_Renewable_Energy_Statistics_2020.pdf"),
    PdfSpec("irena_renewable_power_costs_2022", "IRENA Renewable Power Costs 2022", "2023-08-29", "IRENA", "IRENA_Renewable_power_costs_2022.pdf", "ICLN/NEE", "https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2023/Aug/IRENA_Renewable_power_generation_costs_in_2022.pdf"),
    PdfSpec("iea_breakthrough_agenda_report_2023", "IEA Breakthrough Agenda Report 2023", "2023-09-26", "IEA", "IEA_Breakthrough_Agenda_Report_2023.pdf", "ICLN/NEE", "https://www.iea.org/reports/breakthrough-agenda-report-2023"),
    PdfSpec("iea_renewables_2023_validation", "IEA Renewables 2023", "2024-01-11", "IEA", "IEA_Renewables_2023.pdf", "ICLN/NEE", "https://www.iea.org/reports/renewables-2023"),
    PdfSpec("nextera_annual_2023", "NextEra Energy Annual Report 2023", "2024-02-16", "NextEra Energy", "NextEra_Energy_Annual_Report_2023.pdf", "ETN", "https://www.annualreports.com/HostedData/AnnualReportArchive/n/NYSE_NEE_2023.pdf"),
    PdfSpec("iea_oil_gas_net_zero_2023_validation", "IEA Oil and Gas Industry in Net Zero Transitions", "2023-11-23", "IEA", "IEA_Oil_Gas_Net_Zero_Transitions.pdf", "XLE/XOM transition pressure", "https://www.iea.org/reports/the-oil-and-gas-industry-in-net-zero-transitions"),
    PdfSpec("ipcc_ar6_synthesis", "IPCC AR6 Synthesis Report", "2023-03-20", "IPCC", "IPCC_AR6_SYR_FullVolume.pdf", "Climate risk", "https://www.ipcc.ch/report/ar6/syr/downloads/report/IPCC_AR6_SYR_FullVolume.pdf"),
    PdfSpec("iea_electricity_grids_2023", "IEA Electricity Grids and Secure Energy Transitions", "2023-10-17", "IEA", "IEA_Electricity_Grids_Secure_Energy_Transitions_2023.pdf", "ETN", "https://www.iea.org/reports/electricity-grids-and-secure-energy-transitions"),
    PdfSpec("iea_weo_2022", "IEA World Energy Outlook 2022", "2022-10-27", "IEA", "IEA_World_Energy_Outlook_2022.pdf", "ICLN/NEE", "https://www.iea.org/reports/world-energy-outlook-2022"),
    PdfSpec("iea_electricity_2024", "IEA Electricity 2024", "2024-01-24", "IEA", "IEA_Electricity_2024.pdf", "ETN", "https://www.iea.org/reports/electricity-2024"),
    PdfSpec("iea_power_sector_2021", "IEA Secure Energy Transitions in the Power Sector", "2021-10-27", "IEA", "IEA_Secure_Energy_Transitions_Power_Sector_2021.pdf", "ETN", "https://www.iea.org/reports/secure-energy-transitions-in-the-power-sector"),
    PdfSpec("iea_oil_2024", "IEA Oil 2024", "2024-06-12", "IEA", "IEA_Oil_2024.pdf", "XLE/XOM transition pressure", "https://www.iea.org/reports/oil-2024"),
    PdfSpec("iea_gas_2023", "IEA Medium-Term Gas Report 2023", "2023-10-10", "IEA", "IEA_Medium_Term_Gas_Report_2023.pdf", "XLE/XOM transition pressure", "https://www.iea.org/reports/medium-term-gas-report-2023"),
    PdfSpec("iea_coal_2023", "IEA Coal 2023", "2023-12-15", "IEA", "IEA_Coal_2023.pdf", "XLE/XOM transition pressure", "https://www.iea.org/reports/coal-2023"),
    PdfSpec("iea_global_ev_2023", "IEA Global EV Outlook 2023", "2023-04-26", "IEA", "IEA_Global_EV_Outlook_2023.pdf", "ICLN/NEE", "https://www.iea.org/reports/global-ev-outlook-2023"),
    PdfSpec("iea_solar_pv_supply_2022", "IEA Solar PV Global Supply Chains 2022", "2022-08-01", "IEA", "IEA_Solar_PV_Global_Supply_Chains_2022.pdf", "ICLN/NEE", "https://www.iea.org/reports/solar-pv-global-supply-chains"),
    PdfSpec("iea_clean_tech_supply_2022", "IEA Securing Clean Energy Technology Supply Chains", "2022-07-12", "IEA", "IEA_Securing_Clean_Energy_Tech_Supply_Chains_2022.pdf", "ICLN/NEE", "https://www.iea.org/reports/securing-clean-energy-technology-supply-chains"),
    PdfSpec("iea_etp_2023", "IEA Energy Technology Perspectives 2023", "2023-01-12", "IEA", "IEA_Energy_Technology_Perspectives_2023.pdf", "ICLN/NEE", "https://www.iea.org/reports/energy-technology-perspectives-2023"),
    PdfSpec("iea_weo_2023_validation", "IEA World Energy Outlook 2023", "2023-10-24", "IEA", "IEA_World_Energy_Outlook_2023.pdf", "ICLN/NEE", "https://www.iea.org/reports/world-energy-outlook-2023"),
    PdfSpec("iea_batteries_2024", "IEA Batteries and Secure Energy Transitions 2024", "2024-04-25", "IEA", "IEA_Batteries_Secure_Energy_Transitions_2024.pdf", "ETN", "https://www.iea.org/reports/batteries-and-secure-energy-transitions"),
    PdfSpec("eia_electric_power_annual_2023", "EIA Electric Power Annual 2023", "2024-11-07", "EIA", "EIA_Electric_Power_Annual_2023.pdf", "ETN", "https://www.eia.gov/electricity/annual/archive/2023/pdf/epa.pdf"),
    PdfSpec("exxon_acs_2024", "ExxonMobil Advancing Climate Solutions 2024", "2024-04-08", "ExxonMobil", "ExxonMobil_Advancing_Climate_Solutions_2024.pdf", "Climate risk", "https://corporate.exxonmobil.com/-/media/global/files/advancing-climate-solutions/2024/2024-advancing-climate-solutions-report.pdf"),
    PdfSpec("exxon_acs_2025", "ExxonMobil Advancing Climate Solutions 2025", "2025-03-31", "ExxonMobil", "ExxonMobil_Advancing_Climate_Solutions_2025.pdf", "Climate risk", "https://corporate.exxonmobil.com/-/media/global/files/advancing-climate-solutions/2025/advancing-climate-solutions-report.pdf"),
    PdfSpec("ipcc_ar6_wg3_mitigation", "IPCC AR6 WGIII Mitigation Full Report", "2022-04-04", "IPCC", "IPCC_AR6_WGIII_Mitigation_FullReport.pdf", "Climate risk", "https://www.ipcc.ch/report/ar6/wg3/downloads/report/IPCC_AR6_WGIII_FullReport.pdf"),
    PdfSpec("iea_world_energy_investment_2024", "IEA World Energy Investment 2024", "2024-06-06", "IEA", "IEA_World_Energy_Investment_2024.pdf", "ICLN/NEE", "https://www.iea.org/reports/world-energy-investment-2024"),
    PdfSpec("iea_weo_2024", "IEA World Energy Outlook 2024", "2024-10-16", "IEA", "IEA_World_Energy_Outlook_2024.pdf", "ICLN/NEE", "https://www.iea.org/reports/world-energy-outlook-2024"),
    PdfSpec("iea_renewables_2024", "IEA Renewables 2024", "2024-10-09", "IEA", "IEA_Renewables_2024.pdf", "ICLN/NEE", "https://www.iea.org/reports/renewables-2024"),
    PdfSpec("iea_global_ev_2024", "IEA Global EV Outlook 2024", "2024-04-23", "IEA", "IEA_Global_EV_Outlook_2024.pdf", "ICLN/NEE", "https://www.iea.org/reports/global-ev-outlook-2024"),
    PdfSpec("iea_global_critical_minerals_2024", "IEA Global Critical Minerals Outlook 2024", "2024-05-17", "IEA", "IEA_Global_Critical_Minerals_Outlook_2024.pdf", "ICLN/NEE", "https://www.iea.org/reports/global-critical-minerals-outlook-2024"),
    PdfSpec("iea_coal_2024", "IEA Coal 2024", "2024-12-18", "IEA", "IEA_Coal_2024.pdf", "XLE/XOM transition pressure", "https://www.iea.org/reports/coal-2024"),
    PdfSpec("iea_oil_2025", "IEA Oil 2025", "2025-06-17", "IEA", "IEA_Oil_2025.pdf", "XLE/XOM transition pressure", "https://www.iea.org/reports/oil-2025"),
    PdfSpec("iea_electricity_2025", "IEA Electricity 2025", "2025-02-14", "IEA", "IEA_Electricity_2025.pdf", "ETN", "https://www.iea.org/reports/electricity-2025"),
    PdfSpec("iea_energy_and_ai", "IEA Energy and AI", "2025-04-10", "IEA", "IEA_Energy_and_AI.pdf", "ETN", "https://www.iea.org/reports/energy-and-ai"),
    PdfSpec("iea_energy_technology_perspectives_2024", "IEA Energy Technology Perspectives 2024", "2024-10-30", "IEA", "IEA_Energy_Technology_Perspectives_2024.pdf", "ICLN/NEE", "https://www.iea.org/reports/energy-technology-perspectives-2024"),
    PdfSpec("irena_renewable_capacity_statistics_2024", "IRENA Renewable Capacity Statistics 2024", "2024-03-27", "IRENA", "IRENA_Renewable_Capacity_Statistics_2024.pdf", "ICLN/NEE", "https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2024/Mar/IRENA_RE_Capacity_Statistics_2024.pdf"),
    PdfSpec("iea_global_methane_tracker_2024", "IEA Global Methane Tracker 2024", "2024-03-13", "IEA", "IEA_Global_Methane_Tracker_2024.pdf", "XLE/XOM transition pressure", "https://www.iea.org/reports/global-methane-tracker-2024"),
    PdfSpec("ipcc_ar6_wg1_physical_science", "IPCC AR6 WGI Physical Science Basis", "2021-08-09", "IPCC", "IPCC_AR6_WGI_FullReport.pdf", "Climate risk", "https://www.ipcc.ch/report/ar6/wg1/downloads/report/IPCC_AR6_WGI_FullReport.pdf"),
    PdfSpec("iea_energy_efficiency_2024", "IEA Energy Efficiency 2024", "2024-11-18", "IEA", "IEA_Energy_Efficiency_2024.pdf", "ETN", "https://www.iea.org/reports/energy-efficiency-2024"),
    PdfSpec("eia_electric_power_annual_2022", "EIA Electric Power Annual 2022", "2023-11-02", "EIA", "EIA_Electric_Power_Annual_2022.pdf", "ETN", "https://www.eia.gov/electricity/annual/archive/2022/pdf/epa.pdf"),
    PdfSpec("eia_annual_energy_outlook_2023", "EIA Annual Energy Outlook 2023", "2023-03-16", "EIA", "EIA_Annual_Energy_Outlook_2023.pdf", "XLE/XOM transition pressure", "https://www.eia.gov/outlooks/aeo/pdf/AEO2023_Narrative.pdf"),
    PdfSpec("iea_global_hydrogen_review_2024", "IEA Global Hydrogen Review 2024", "2024-10-02", "IEA", "IEA_Global_Hydrogen_Review_2024.pdf", "ICLN/NEE", "https://www.iea.org/reports/global-hydrogen-review-2024"),
    PdfSpec("eaton_annual_2023_validation", "Eaton Annual Report 2023", "2024-02-23", "Eaton", "Eaton_Annual_Report_2023.pdf", "ETN", "https://www.annualreports.com/HostedData/AnnualReportArchive/e/NYSE_ETN_2023.pdf"),
    PdfSpec("iea_the_future_of_heat_pumps", "IEA The Future of Heat Pumps", "2022-11-30", "IEA", "IEA_The_Future_of_Heat_Pumps.pdf", "ETN", "https://www.iea.org/reports/the-future-of-heat-pumps"),
    PdfSpec("iea_energy_efficiency_2023", "IEA Energy Efficiency 2023", "2023-11-29", "IEA", "IEA_Energy_Efficiency_2023.pdf", "ETN", "https://www.iea.org/reports/energy-efficiency-2023"),
    PdfSpec("iea_renewable_energy_market_update_2022", "IEA Renewable Energy Market Update May 2022", "2022-05-11", "IEA", "IEA_Renewable_Energy_Market_Update_May_2022.pdf", "ICLN/NEE", "https://www.iea.org/reports/renewable-energy-market-update-may-2022"),
    PdfSpec("iea_net_zero_roadmap_2023", "IEA Net Zero Roadmap 2023 Update", "2023-09-26", "IEA", "IEA_Net_Zero_Roadmap_2023_Update.pdf", "Climate risk", "https://www.iea.org/reports/net-zero-roadmap-a-global-pathway-to-keep-the-15-0c-goal-in-reach"),
    PdfSpec("iea_clean_energy_market_monitor_march_2024", "IEA Clean Energy Market Monitor March 2024", "2024-03-01", "IEA", "IEA_Clean_Energy_Market_Monitor_March_2024.pdf", "ICLN/NEE", "https://www.iea.org/reports/clean-energy-market-monitor-march-2024"),
    PdfSpec("iea_renewable_energy_market_update_june_2023", "IEA Renewable Energy Market Update June 2023", "2023-06-01", "IEA", "IEA_Renewable_Energy_Market_Update_June_2023.pdf", "ICLN/NEE", "https://www.iea.org/reports/renewable-energy-market-update-june-2023"),
    PdfSpec("iea_emissions_2023", "IEA CO2 Emissions in 2023", "2024-03-01", "IEA", "IEA_CO2_Emissions_in_2023.pdf", "Climate risk", "https://www.iea.org/reports/co2-emissions-in-2023"),
]


def _request(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 validation-pdf-downloader"})
    with urlopen(request, timeout=90) as response:
        return response.read()


def _resolve_pdf_url(source: str) -> str:
    if source.lower().split("?")[0].endswith(".pdf"):
        return source
    html = _request(source).decode("utf-8", errors="ignore")
    candidates = re.findall(r'https?://[^"\']+?\.pdf(?:\?[^"\']*)?', html)
    if not candidates:
        candidates = [urljoin(source, match) for match in re.findall(r'href=["\']([^"\']+?\.pdf(?:\?[^"\']*)?)["\']', html)]
    if not candidates:
        raise RuntimeError(f"No PDF link found on {source}")
    preferred = [url for url in candidates if "iea.blob.core.windows.net" in url or "/downloads/" in url]
    return (preferred or candidates)[0].replace("&amp;", "&")


def _looks_like_pdf(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 1000:
        return False
    with path.open("rb") as handle:
        return handle.read(4) == b"%PDF"


def download_pdf(spec: PdfSpec) -> dict:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    target = PDF_DIR / spec.filename
    resolved_url = ""
    status = "exists"
    error = ""

    if not _looks_like_pdf(target):
        status = "downloaded"
        try:
            resolved_url = _resolve_pdf_url(spec.source)
            data = _request(resolved_url)
            target.write_bytes(data)
            if not _looks_like_pdf(target):
                target.unlink(missing_ok=True)
                raise RuntimeError("Downloaded file is not a valid PDF")
            time.sleep(0.2)
        except Exception as exc:
            status = "failed"
            error = str(exc)
    else:
        resolved_url = spec.source

    return {
        "file": spec.filename,
        "issuer": spec.issuer,
        "title": spec.title,
        "expected_hint": spec.expected_hint,
        "saved_locally": _looks_like_pdf(target),
        "bytes": target.stat().st_size if target.exists() else 0,
        "source_url": resolved_url or spec.source,
        "download_status": status,
        "error": error,
    }


def write_catalog() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with CATALOG_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["report_id", "title", "date", "issuer", "path", "expected_hint", "source_url"],
        )
        writer.writeheader()
        for spec in PDF_SPECS:
            writer.writerow(
                {
                    "report_id": spec.report_id,
                    "title": spec.title,
                    "date": spec.date,
                    "issuer": spec.issuer,
                    "path": f"data/sample_pdfs/{spec.filename}",
                    "expected_hint": spec.expected_hint,
                    "source_url": spec.source,
                }
            )


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(PDF_SPECS)
    specs = PDF_SPECS[:limit]
    write_catalog()
    rows = [download_pdf(spec) for spec in specs]
    with MANIFEST_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    saved = sum(1 for row in rows if row["saved_locally"])
    failed = [row for row in rows if not row["saved_locally"]]
    print(f"catalog={CATALOG_PATH}")
    print(f"manifest={MANIFEST_PATH}")
    print(f"saved={saved}/{len(rows)}")
    for row in failed:
        print(f"failed: {row['file']} - {row['error']}")


if __name__ == "__main__":
    main()
