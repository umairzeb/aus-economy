"""Directly-sourced series. Each entry pulls one ABS or RBA time series.

Derived series (growth rates, spliced history, real wages) and bundles
(cross-sections such as exports by country) live in derived.py / bundles.py.

ABS key order is the dataflow's dimension order, e.g. LF is
MEASURE.SEX.AGE.TSEST.REGION.FREQ. TSEST: 10 original, 20 seasonally
adjusted, 30 trend.
"""

ABS_FLOWS = {
    "CPI": "Consumer Price Index",
    "CPI_M": "Monthly CPI Indicator (discontinued 2025)",
    "CPI_Q": "Consumer Price Index, quarterly analytical series",
    "LF": "Labour Force, Australia",
    "LF_UNDER": "Labour Force: underemployment and underutilisation",
    "WPI": "Wage Price Index",
    "JV": "Job Vacancies",
    "ANA_AGG": "National Accounts: key aggregates",
    "ANA_IND_GVA": "National Accounts: production (GDP by industry)",
    "ITGS": "International Trade in Goods",
    "BOP": "Balance of Payments",
    "MERCH_EXP": "Merchandise Exports by commodity and country",
    "RES_DWELL_ST": "Total Value of Dwellings",
    "LEND_HOUSING": "Lending Indicators: housing finance",
    "BA_GCCSA": "Building Approvals",
    "ERP_COMP_Q": "National, state and territory population",
    "HSI_M": "Monthly Household Spending Indicator",
}

RBA_TABLES = {
    "a2": "A2 Monetary policy changes",
    "f2": "F2 Capital market yields, government bonds (daily)",
    "f2.1": "F2.1 Capital market yields, government bonds (monthly)",
    "f5": "F5 Indicator lending rates",
    "f11": "F11 Exchange rates (monthly)",
    "e2": "E2 Household finances, selected ratios",
}

# Series with `rba_hist` splice a frozen RBA history workbook in front of the
# current CSV, extending them back to 1969.

# section: prices | jobs | growth | trade | housing | population | money | spending | budget
SERIES = [
    # --- Jobs ---
    dict(id="unemployment_rate", title="Unemployment rate", unit="%", section="jobs", freq="M",
         abs=("LF", "M13.3.1599.20.AUS.M")),
    dict(id="participation_rate", title="Participation rate", unit="%", section="jobs", freq="M",
         abs=("LF", "M12.3.1599.20.AUS.M")),
    dict(id="employed_persons", title="Employed persons", unit="'000", section="jobs", freq="M",
         abs=("LF", "M3.3.1599.20.AUS.M"), to_mult=3),
    dict(id="underemployment_rate", title="Underemployment rate", unit="%", section="jobs", freq="M",
         abs=("LF_UNDER", "M23.3.1599.20.AUS.M"),
         notes="Employed people who want, and are available for, more hours. Share of the labour force."),
    dict(id="underutilisation_rate", title="Underutilisation rate", unit="%", section="jobs", freq="M",
         abs=("LF_UNDER", "M24.3.1599.20.AUS.M"),
         notes="Unemployment rate plus underemployment rate."),
    dict(id="youth_unemployment_rate", title="Youth unemployment rate (15-24)", unit="%", section="jobs", freq="M",
         abs=("LF_UNDER", "M13.3.1524.20.AUS.M")),
    dict(id="wpi_yoy", title="Wage growth (Wage Price Index)", unit="% y/y", section="jobs", freq="Q",
         abs=("WPI", "3.THRPEB.7.TOT.20.AUS.Q"),
         notes="Hourly rates of pay excluding bonuses, private and public sector."),
    dict(id="job_vacancies", title="Job vacancies", unit="'000", section="jobs", freq="Q",
         abs=("JV", "M1.7.TOT.20.AUS.Q"), to_mult=3),

    # --- Growth ---
    dict(id="gdp_real", title="Real GDP", unit="$m (chain volume)", section="growth", freq="Q",
         abs=("ANA_AGG", "M1.GPM.20.AUS.Q"), to_mult=6),
    dict(id="gdp_nominal", title="Nominal GDP", unit="$m", section="growth", freq="Q",
         abs=("ANA_AGG", "M3.GPM.20.AUS.Q"), to_mult=6),
    dict(id="gdp_per_capita_real", title="Real GDP per person", unit="$ (chain volume)", section="growth", freq="Q",
         abs=("ANA_AGG", "M1.GPM_PCA.20.AUS.Q"), to_mult=0),
    dict(id="household_saving_ratio", title="Household saving ratio", unit="%", section="growth", freq="Q",
         abs=("ANA_AGG", "M7.HSR.20.AUS.Q")),
    dict(id="terms_of_trade", title="Terms of trade", unit="index", section="trade", freq="Q",
         abs=("ANA_AGG", "M5.TTR.20.AUS.Q"),
         notes="Export prices relative to import prices. Higher means the world pays more for what Australia sells."),

    # --- Trade ---
    dict(id="exports_goods", title="Goods exports", unit="$m", section="trade", freq="M",
         abs=("ITGS", "M1.1000.20.AUS.M"), to_mult=6),
    dict(id="imports_goods", title="Goods imports", unit="$m", section="trade", freq="M",
         abs=("ITGS", "M1.2000.20.AUS.M"), to_mult=6, negate=True),
    dict(id="trade_balance_goods", title="Goods trade balance", unit="$m", section="trade", freq="M",
         abs=("ITGS", "M1.170.20.AUS.M"), to_mult=6),
    dict(id="exports_services", title="Services exports", unit="$m", section="trade", freq="Q",
         abs=("BOP", "1.4000.20.Q"), to_mult=6),
    dict(id="imports_services", title="Services imports", unit="$m", section="trade", freq="Q",
         abs=("BOP", "1.6000.20.Q"), to_mult=6, negate=True),
    dict(id="exports_education_q", title="Education exports (international students)", unit="$m", section="trade",
         freq="Q", abs=("BOP", "1.4505.10.Q"), to_mult=6, hidden=True),

    # --- Housing ---
    dict(id="dwelling_mean_price", title="Mean dwelling price", unit="$'000", section="housing", freq="Q",
         abs=("RES_DWELL_ST", "5.AUS.Q"), to_mult=3),
    dict(id="lending_owner_occupier", title="New owner-occupier home loans", unit="$m", section="housing", freq="Q",
         abs=("LEND_HOUSING", "FIN_VAL.NEWCOMMITS.DV8368.TOTDWELL.TOT.DV5167.20.AUS.Q"), to_mult=6),
    dict(id="lending_investor", title="New investor home loans", unit="$m", section="housing", freq="Q",
         abs=("LEND_HOUSING", "FIN_VAL.NEWCOMMITS.DV8368.TOTDWELL.TOT.DV5168.20.AUS.Q"), to_mult=6),
    dict(id="lending_first_home_buyer", title="New first home buyer loans", unit="$m", section="housing", freq="Q",
         abs=("LEND_HOUSING", "FIN_VAL.NEWCOMMITS.DV8368.TOTHOUS.TOT.DV5167_FHB.20.AUS.Q"), to_mult=6),
    dict(id="dwelling_approvals_m", title="Dwelling approvals (monthly, original)", unit="dwellings",
         section="housing", freq="M", abs=("BA_GCCSA", "1.1.9.TOT.100.10.AUS.M"), to_mult=0, hidden=True),
    dict(id="mortgage_rate_variable", title="Standard variable mortgage rate (banks)", unit="%", section="housing",
         freq="M", rba=("f5", "FILRHLBVS")),
    dict(id="mortgage_rate_discounted", title="Discounted variable mortgage rate (banks)", unit="%",
         section="housing", freq="M", rba=("f5", "FILRHLBVD"),
         notes="Closer to what new borrowers actually pay."),
    dict(id="household_debt_to_income", title="Household debt to income", unit="%", section="housing", freq="Q",
         rba=("e2", "BHFDDIT")),

    # --- Population ---
    dict(id="population", title="Population", unit="people", section="population", freq="Q",
         abs=("ERP_COMP_Q", "10.AUS.Q"), to_mult=0),
    dict(id="nom_q", title="Net overseas migration (quarter)", unit="people", section="population", freq="Q",
         abs=("ERP_COMP_Q", "9.AUS.Q"), to_mult=0, hidden=True),
    dict(id="natural_increase_q", title="Natural increase (quarter)", unit="people", section="population", freq="Q",
         abs=("ERP_COMP_Q", "3.AUS.Q"), to_mult=0, hidden=True),

    # --- Money & markets ---
    dict(id="cash_rate", title="RBA cash rate target", unit="%", section="money", freq="event",
         rba=("a2", "ARBAMPCNCRT"), notes="One point per RBA decision; draw as a step line."),
    dict(id="bond_10y", title="10-year government bond yield", unit="%", section="money", freq="M",
         rba=("f2.1", "FCMYGBAG10"), rba_hist="f02histhist"),
    dict(id="aud_usd", title="AUD/USD", unit="US$", section="money", freq="M", rba=("f11", "FXRUSD"),
         rba_hist="f11hist-1969-2009"),
    dict(id="aud_twi", title="AUD trade-weighted index", unit="index", section="money", freq="M",
         rba=("f11", "FXRTWI"), rba_hist="f11hist-1969-2009"),

    # --- Spending ---
    dict(id="household_spending_yoy", title="Household spending growth", unit="% y/y", section="spending",
         freq="M", abs=("HSI_M", "9.TOT.CUR.20.AUS.M"), notes="Current prices, so includes inflation."),
]

# CPI components: monthly, original, annual % change (CPI MEASURE 3).
CPI_COMPONENTS = {
    "food": ("20001", "Food & non-alcoholic drinks"),
    "housing": ("20003", "Housing"),
    "rents": ("30014", "Rents"),
    "electricity": ("40055", "Electricity"),
    "insurance": ("115529", "Insurance"),
    "fuel": ("40081", "Petrol & fuel"),
    "transport": ("20005", "Transport"),
    "health": ("115486", "Health"),
    "education": ("115493", "Education"),
    "child_care": ("115498", "Child care"),
    "meals_out": ("30007", "Meals out & takeaway"),
    "alcohol_tobacco": ("20006", "Alcohol & tobacco"),
    "clothing": ("20002", "Clothing & footwear"),
    "furnishings": ("20004", "Furnishings & household"),
    "communication": ("115488", "Communication"),
    "recreation": ("115489", "Recreation & culture"),
    "insurance_financial": ("126670", "Insurance & financial services"),
}

STATES = {"1": "NSW", "2": "VIC", "3": "QLD", "4": "SA", "5": "WA", "6": "TAS", "7": "NT", "8": "ACT"}
