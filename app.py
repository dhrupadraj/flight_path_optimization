import streamlit as st

# -----------------------------
# Sidebar: Flight Configuration
# -----------------------------
st.sidebar.title("✈️ Flight Route Optimization")

# Airport selection
st.sidebar.subheader("Airports")
INDIAN_AIRPORTS = {
    "Indira Gandhi Intl – Delhi (DEL)": "DEL",
    "Chhatrapati Shivaji Intl – Mumbai (BOM)": "BOM",
    "Kempegowda Intl – Bengaluru (BLR)": "BLR",
    "Rajiv Gandhi Intl – Hyderabad (HYD)": "HYD",
    "Chennai Intl – Chennai (MAA)": "MAA",
    "Netaji Subhas Chandra Bose Intl – Kolkata (CCU)": "CCU",

    # South India
    "Cochin Intl – Kochi (COK)": "COK",
    "Trivandrum Intl – Thiruvananthapuram (TRV)": "TRV",
    "Kannur Intl – Kannur (CNN)": "CNN",
    "Coimbatore Intl – Coimbatore (CJB)": "CJB",
    "Madurai Intl – Madurai (IXM)": "IXM",
    "Tiruchirappalli Intl – Tiruchirappalli (TRZ)": "TRZ",
    "Mangaluru Intl – Mangaluru (IXE)": "IXE",
    "Vijayawada Intl – Vijayawada (VGA)": "VGA",
    "Visakhapatnam Intl – Visakhapatnam (VTZ)": "VTZ",
    "Tirupati Intl – Tirupati (TIR)": "TIR",

    # West India
    "Sardar Vallabhbhai Patel Intl – Ahmedabad (AMD)": "AMD",
    "Pune Intl – Pune (PNQ)": "PNQ",
    "Goa Intl – Dabolim (GOI)": "GOI",
    "Manohar Intl – Mopa, Goa (GOX)": "GOX",
    "Vadodara Intl – Vadodara (BDQ)": "BDQ",
    "Surat Intl – Surat (STV)": "STV",
    "Rajkot Intl – Rajkot (RAJ)": "RAJ",

    # North India
    "Jaipur Intl – Jaipur (JAI)": "JAI",
    "Chandigarh Intl – Chandigarh (IXC)": "IXC",
    "Amritsar Intl – Amritsar (ATQ)": "ATQ",
    "Lucknow Intl – Lucknow (LKO)": "LKO",
    "Varanasi Intl – Varanasi (VNS)": "VNS",
    "Dehradun – Jolly Grant (DED)": "DED",
    "Jammu – Satwari (IXJ)": "IXJ",
    "Srinagar Intl – Srinagar (SXR)": "SXR",

    # East & North-East India
    "Lokpriya Gopinath Bordoloi Intl – Guwahati (GAU)": "GAU",
    "Bagdogra Intl – Bagdogra (IXB)": "IXB",
    "Imphal Intl – Imphal (IMF)": "IMF",
    "Agartala Intl – Agartala (IXA)": "IXA",
    "Dibrugarh – Mohanbari (DIB)": "DIB",
    "Silchar – Kumbhirgram (IXS)": "IXS",

    # Central India
    "Dr. Babasaheb Ambedkar Intl – Nagpur (NAG)": "NAG",
    "Bhopal – Raja Bhoj (BHO)": "BHO",
    "Indore – Devi Ahilyabai Holkar (IDR)": "IDR",
    "Raipur – Swami Vivekananda (RPR)": "RPR",

    # Islands
    "Veer Savarkar Intl – Port Blair (IXZ)": "IXZ"
}

airport_labels = list(INDIAN_AIRPORTS.keys())

# Departure (searchable by default)
departure_label = st.sidebar.selectbox(
    "Departure Airport",
    airport_labels,
    help="Search and select departure airport"
)

# Filter arrival airports to prevent same selection
arrival_options = [a for a in airport_labels if a != departure_label]

arrival_label = st.sidebar.selectbox(
    "Arrival Airport",
    arrival_options,
    help="Arrival airport must be different from departure"
)

# Flight parameters
st.sidebar.subheader("Flight Parameters")

cruise_altitude = st.sidebar.selectbox(
    "Cruise Altitude (ft)",
    options=[30000, 32000, 34000, 36000, 38000],
    index=2
)

departure_time = st.sidebar.time_input(
    "Departure Time (UTC)"
)

date = st.sidebar.date_input(
    "Flight Date"
)

# Optimization settings
st.sidebar.subheader("Optimization Settings")

optimize_for = st.sidebar.radio(
    "Optimize For",
    options=[
        "Minimum Time",
        "Fuel Efficiency",
        "Balanced (Time + Fuel)"
    ]
)

wind_weight = st.sidebar.slider(
    "Wind Influence Weight",
    min_value=0.0,
    max_value=1.0,
    value=0.7,
    step=0.05,
    help="Higher value prioritizes tailwinds"
)

# -----------------------------
# Sidebar: Actions
# -----------------------------
st.sidebar.subheader("Actions")

show_straight_route = st.sidebar.button(
    "Show Original Route"
)

show_optimized_route = st.sidebar.button(
    "Show Optimized Route"
)

st.sidebar.markdown("---")

download_csv = st.sidebar.button(
    "Download Route CSV"
)

generate_report = st.sidebar.button(
    "Generate Flight Report"
)
