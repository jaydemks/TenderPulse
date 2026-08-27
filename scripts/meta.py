"""Reference data: CPV divisions and country codes."""

CPV_DIVISIONS = {
    "03": "Agriculture, farming, fishing and forestry products",
    "09": "Petroleum products, fuel, electricity and energy",
    "14": "Mining, basic metals and related products",
    "15": "Food, beverages and tobacco",
    "16": "Agricultural machinery",
    "18": "Clothing, footwear and accessories",
    "19": "Leather, textile, plastic and rubber materials",
    "22": "Printed matter and related products",
    "24": "Chemical products",
    "30": "Office and computing machinery and supplies",
    "31": "Electrical machinery, equipment and lighting",
    "32": "Radio, television and telecommunication equipment",
    "33": "Medical equipment and pharmaceuticals",
    "34": "Transport equipment",
    "35": "Security, fire-fighting, police and defence equipment",
    "37": "Musical instruments, sport goods, games and art materials",
    "38": "Laboratory, optical and precision equipment",
    "39": "Furniture, furnishings and cleaning products",
    "41": "Collected and purified water",
    "42": "Industrial machinery",
    "43": "Mining, quarrying and construction machinery",
    "44": "Construction structures and materials",
    "45": "Construction work",
    "48": "Software packages and information systems",
    "50": "Repair and maintenance services",
    "51": "Installation services",
    "55": "Hotel, restaurant and retail trade services",
    "60": "Transport services",
    "63": "Supporting transport services and travel agencies",
    "64": "Postal and telecommunications services",
    "65": "Public utilities",
    "66": "Financial and insurance services",
    "70": "Real estate services",
    "71": "Architectural, engineering and inspection services",
    "72": "IT services: consulting, software development and support",
    "73": "Research and development services",
    "75": "Administration, defence and social security services",
    "76": "Services related to the oil and gas industry",
    "77": "Agricultural, forestry and horticultural services",
    "79": "Business services: law, marketing, consulting, recruitment",
    "80": "Education and training services",
    "85": "Health and social work services",
    "90": "Sewage, refuse, cleaning and environmental services",
    "92": "Recreational, cultural and sporting services",
    "98": "Other community, social and personal services",
}

COUNTRIES = {
    "AUT": "Austria", "BEL": "Belgium", "BGR": "Bulgaria", "CYP": "Cyprus",
    "CZE": "Czechia", "DEU": "Germany", "DNK": "Denmark", "EST": "Estonia",
    "ESP": "Spain", "FIN": "Finland", "FRA": "France", "GRC": "Greece",
    "HRV": "Croatia", "HUN": "Hungary", "IRL": "Ireland", "ITA": "Italy",
    "LTU": "Lithuania", "LUX": "Luxembourg", "LVA": "Latvia", "MLT": "Malta",
    "NLD": "Netherlands", "POL": "Poland", "PRT": "Portugal", "ROU": "Romania",
    "SWE": "Sweden", "SVN": "Slovenia", "SVK": "Slovakia",
    "NOR": "Norway", "ISL": "Iceland", "LIE": "Liechtenstein", "CHE": "Switzerland",
    "GBR": "United Kingdom", "TUR": "Turkey", "SRB": "Serbia", "MKD": "North Macedonia",
    "ALB": "Albania", "BIH": "Bosnia and Herzegovina", "MNE": "Montenegro",
    "UKR": "Ukraine", "MDA": "Moldova", "GEO": "Georgia", "XKX": "Kosovo",
}

CONTRACT_NATURE = {
    "works": "Works", "supplies": "Supplies", "services": "Services",
}

def cpv_division(code):
    return (code or "")[:2]

def cpv_label(div):
    return CPV_DIVISIONS.get(div, "Other")

def country_name(code):
    return COUNTRIES.get(code, code or "Unknown")
