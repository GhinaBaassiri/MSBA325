import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import io
import plotly.express as px

# Set page config
st.set_page_config(page_title="Public Spaces Dashboard", page_icon="🏙️", layout="wide")

# Header
st.title("🏙️ Public Spaces Lebanon 2023 Dashboard")
st.markdown("Explore lighting and park conditions across different areas")
st.markdown("---")

# Load data function
@st.cache_data
def load_data():
    url = 'https://linked.aub.edu.lb/pkgcube/data/22fb9db8977546c7219d549143714902_20240905_224655.csv'
    response = requests.get(url)
    df = pd.read_csv(io.StringIO(response.text))
    
    # Data cleaning and preprocessing (as per your original code)
    df_cleaned = df.copy()
    df_cleaned.columns = df_cleaned.columns.str.strip()
    columns_to_drop = ['Observation URI', 'dataset', 'publisher']
    df_cleaned = df_cleaned.drop(columns=columns_to_drop)
    df_cleaned = df_cleaned.rename(columns={'Existence of public parks - exists': 'Public Parks Exist'})
    
    def clean_ref_area(url):
        return url.split('/')[-1].replace('_', ' ')
    
    df_cleaned['Area'] = df_cleaned['refArea'].apply(clean_ref_area)
    df_cleaned = df_cleaned.drop(columns=['refArea', 'references'])
    
    column_order = ['Area', 'Public Parks Exist'] + [col for col in df_cleaned.columns if col not in ['Area', 'Public Parks Exist']]
    df_cleaned = df_cleaned[column_order]
    
    df = df_cleaned.rename(columns={
        'Public Parks Exist': 'parks_exist',
        'State of public parks - bad': 'parks_bad',
        'State of the lighting network - bad': 'lighting_bad',
        'State of the lighting network - acceptable': 'lighting_acceptable',
        'State of the lighting network - good': 'lighting_good',
        'State of public parks - good': 'parks_good',
        'State of public parks - acceptable': 'parks_acceptable'
    })
    
    return df

df = load_data()

# Sidebar for user input
st.sidebar.header("Filter Data")
selected_areas = st.sidebar.multiselect("Select Areas", options=df['Area'].unique(), default=df['Area'].unique())

# Filter data based on user selection
filtered_df = df[df['Area'].isin(selected_areas)]

# Create visualizations
def create_stacked_bar_chart(data, columns, title, colors):
    fig = go.Figure()
    for col, color in zip(columns, colors):
        fig.add_trace(go.Bar(
            x=data['Area'],
            y=data[col],
            name=col.replace('_', ' ').title(),
            marker_color=color
        ))
    
    fig.update_layout(
        title=title,
        barmode='stack',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=500,
    )
    return fig

# Lighting conditions visualization
lighting_data = filtered_df.groupby('Area')[['lighting_bad', 'lighting_acceptable', 'lighting_good']].sum().reset_index()
lighting_fig = create_stacked_bar_chart(
    lighting_data,
    ['lighting_bad', 'lighting_acceptable', 'lighting_good'],
    "Lighting Conditions by Area",
    ['#FF9999', '#FFD700', '#90EE90']
)

# Parks conditions visualization
parks_data = filtered_df.groupby('Area')[['parks_bad', 'parks_acceptable', 'parks_good']].sum().reset_index()
parks_fig = create_stacked_bar_chart(
    parks_data,
    ['parks_bad', 'parks_acceptable', 'parks_good'],
    "Park Conditions by Area",
    ['#FF6B6B', '#FFA07A', '#98FB98']
)

# Display visualizations
col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(lighting_fig, use_container_width=True)
    st.markdown("This graph shows the distribution of lighting conditions (bad, acceptable, good) across different areas. Each bar represents an area, and the stacked sections show the proportion of each condition.")

with col2:
    st.plotly_chart(parks_fig, use_container_width=True)
    st.markdown("This graph illustrates the distribution of park conditions (bad, acceptable, good) across different areas. Each bar represents an area, and the stacked sections indicate the proportion of each condition.")


st.header("🌟 Top Areas and Towns with Best Conditions")

# Sidebar for filters
st.sidebar.header("Filters")
view_level = 'Areas'
num_top_entities = st.sidebar.slider(f"Number of top {view_level.lower()} to display", min_value=5, max_value=20, value=10)

# Function to aggregate data
def aggregate_data(data, group_column):
    agg_data = data.groupby(group_column).agg({
        'lighting_good': 'sum',
        'parks_good': 'sum',
        'lighting_acceptable': 'sum',
        'parks_acceptable': 'sum',
        'parks_exist': 'sum',
        'parks_bad': 'sum',
        'lighting_bad': 'sum',
        'Town': 'nunique'  # Count unique towns in each area
    }).reset_index()
    
    agg_data.rename(columns={'Town': 'town_count'}, inplace=True)
    
    # Calculate total score
    agg_data['total_score'] = (
        agg_data['lighting_good'] + 
        agg_data['parks_good'] + 
        agg_data['lighting_acceptable'] + 
        agg_data['parks_acceptable']
    )
    
    # Normalize score by number of towns
    agg_data['normalized_score'] = agg_data['total_score'] / agg_data['town_count']
    
    return agg_data

# Aggregate data based on selected view level
if view_level == 'Areas':
    grouped_df = aggregate_data(df, 'Area')
    score_column = 'normalized_score'
    group_column = 'Area'
else:
    grouped_df = aggregate_data(df, 'Town')
    score_column = 'total_score'  # For towns, we use the raw score
    group_column = 'Town'

# Get top entities
top_entities = grouped_df.nlargest(num_top_entities, score_column)

# Create horizontal bar chart
fig_top_entities = go.Figure()
fig_top_entities.add_trace(go.Bar(
    y=top_entities[group_column],
    x=top_entities[score_column],
    orientation='h',
    marker_color='#1f77b4'
))

fig_top_entities.update_layout(
    title=f"Top {num_top_entities} {view_level} with Best Overall Conditions",
    xaxis_title="Normalized Score" if view_level == 'Areas' else "Total Score",
    yaxis_title=view_level,
    height=500,
)

st.plotly_chart(fig_top_entities, use_container_width=True)

if view_level == 'Areas':
    st.markdown(f"""
    **Understanding the Normalized Score:**
    - The normalized score for each area is calculated by summing 'good' and 'acceptable' conditions for both lighting and parks, then dividing by the number of towns in that area.
    - This normalization reduces bias towards areas with more towns, allowing for fairer comparison.
    - A higher score indicates better overall infrastructure quality relative to the number of towns.
    - The chart above shows the top {num_top_entities} areas based on this normalized scoring system.
    """)
else:
    st.markdown(f"""
    **Understanding the Total Score:**
    - The total score for each town is the sum of 'good' and 'acceptable' conditions for both lighting and parks.
    - Each 'good' or 'acceptable' condition contributes 1 point to the total score.
    - A higher score indicates better overall infrastructure quality.
    - The chart above shows the top {num_top_entities} towns based on this simple scoring system.
    """)

# Interactive feature: Detailed view of selected entity
selected_entity = st.selectbox(f"Select a {view_level.lower()[:-1]} for detailed view", options=top_entities[group_column])

if selected_entity:
    entity_data = top_entities[top_entities[group_column] == selected_entity].iloc[0]
    st.write(f"Detailed information for {selected_entity}:")
    st.write(f"- Lighting (Good): {entity_data['lighting_good']}")
    st.write(f"- Parks (Good): {entity_data['parks_good']}")
    st.write(f"- Lighting (Acceptable): {entity_data['lighting_acceptable']}")
    st.write(f"- Parks (Acceptable): {entity_data['parks_acceptable']}")
    st.write(f"- Parks Exist: {entity_data['parks_exist']}")
    st.write(f"- Lighting (Bad): {entity_data['lighting_bad']}")
    st.write(f"- Parks (Bad): {entity_data['parks_bad']}")
    if view_level == 'Areas':
        st.write(f"- Number of Towns: {entity_data['town_count']}")
        st.write(f"- Total Score: {entity_data['total_score']}")
        st.write(f"- Normalized Score: {entity_data['normalized_score']:.2f}")
    else:
        st.write(f"- Total Score: {entity_data['total_score']}")

    # If viewing Areas, show related towns
    if view_level == 'Areas':
        related_towns = df[df['Area'] == selected_entity]['Town'].unique()
        st.write(f"Towns in {selected_entity}:")
        st.write(", ".join(related_towns))


st.header("📊 Proportion of Conditions by Area")

# List of binary variables
binary_vars = ['parks_exist', 'parks_bad', 'lighting_bad', 'lighting_acceptable', 'lighting_good', 'parks_good', 'parks_acceptable']

# Allow user to select areas for comparison
selected_areas = st.multiselect("Select Areas for Comparison", options=df['Area'].unique(), default=df['Area'].unique()[:4])

# Function to create pie charts for binary variables
def create_binary_pie_charts(data, variables, selected_areas):
    filtered_data = data[data['Area'].isin(selected_areas)]
    
    for i in range(0, len(variables), 2):  # Changed from 4 to 2 charts per row
        fig = make_subplots(rows=1, cols=2, specs=[[{'type': 'domain'}, {'type': 'domain'}]])
        
        for j, var in enumerate(variables[i:i+2]):
            if var in filtered_data.columns:
                pie_data = filtered_data.groupby('Area')[var].sum().reset_index()
                pie_chart = px.pie(
                    pie_data,
                    names='Area',
                    values=var,
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig.add_trace(pie_chart.data[0], row=1, col=j+1)
                
                fig.add_annotation(
                    text=f"Proportion of {var.replace('_', ' ').title()}",
                    x=(j * 0.5) + 0.25,
                    y=1.05,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font_size=14
                )
        
        fig.update_layout(height=400, width=800)
        st.plotly_chart(fig, use_container_width=True)

# Create a container for charts with a max height
chart_container = st.container()
chart_container.markdown("""
<style>
    .chart-container {
        max-height: 800px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)

# Create and display the pie charts if areas are selected
if selected_areas:
    with chart_container:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        create_binary_pie_charts(df, binary_vars, selected_areas)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("""
    These pie charts show the proportion of each condition (parks existence, good/bad/acceptable conditions for parks and lighting) across the selected areas. 
    Each chart represents a specific condition, and the slices show how that condition is distributed among the chosen areas.
    This visualization allows for easy comparison of infrastructure quality and availability across different regions.
    """)

    # Display raw data for verification
    with st.expander("View Raw Data for Selected Areas"):
        st.write(df[df['Area'].isin(selected_areas)][['Area'] + binary_vars])
else:
    st.warning("Please select at least one area for comparison.")

st.markdown("---")
st.markdown("Created by Ghina Baassiri | Data source: AUB")