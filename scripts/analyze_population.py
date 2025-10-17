#!/usr/bin/env python3
"""
NZ 250m Grid population analysis + LLM report & PDF generation
Merged and cleaned version of provided code.
"""

import os
import math
import time
import json
import datetime
import requests
import codecs

import pandas as pd
import re
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import FuncFormatter
from pyproj import Transformer
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# --- Optional LLM (ollama) setup ---
try:
    import ollama  # type: ignore
    _OLLAMA_OK = True
except ImportError:
    ollama = None
    _OLLAMA_OK = False

model_name = "llama2"  # change if needed

# --- Load grid data ---
# Adjust path as needed
GEOJSON_PATH = "../data/nz_population.geojson"
try:
    grid = gpd.read_file(GEOJSON_PATH)
except Exception as e:
    print(f"Error: Could not read GeoJSON file at {GEOJSON_PATH}. Please ensure the file exists and is valid.")
    print(f"Details: {e}")
    exit()

# keep columns you expect (defensive)
expected_cols = ['GridID', 'PopEst2023', 'geometry', 'CENTROID_X', 'CENTROID_Y']
existing = [c for c in expected_cols if c in grid.columns]
grid = grid[existing].copy()

# Check/convert coordinate system (NZTM2000)
if grid.crs is None or grid.crs.to_epsg() != 2193:
    print("DEBUG: Reprojecting grid to EPSG:2193 (NZTM2000)")
    grid = grid.to_crs(epsg=2193)

# --- Utilities ---

def split_dataframe(df, chunk_size):
    num_chunks = math.ceil(len(df) / chunk_size)
    return [df.iloc[i*chunk_size:(i+1)*chunk_size].copy() for i in range(num_chunks)]

cache = {}

def get_placename_from_coords(lon, lat, email_contact="contact@example.com"):
    key = (round(lon, 3), round(lat, 3))
    if key in cache:
        return cache[key]

    nominatim_url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1"
    headers = {'User-Agent': f'NZPopulationAnalysis/1.0 ({email_contact})'}

    try:
        resp = requests.get(nominatim_url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        addr = data.get('address', {})
        placename = (
            addr.get('city') or addr.get('town') or addr.get('village') or
            addr.get('suburb') or addr.get('county') or addr.get('state') or
            addr.get('country') or data.get('display_name', '').split(',')[0]
        )
        placename = placename or f"Unknown Region ({lat:.2f},{lon:.2f})"
        cache[key] = placename
        return placename
    except requests.exceptions.RequestException as e:
        print(f"Error during Nominatim request for {lat},{lon}: {e}")
        return f"Error Region ({lat:.2f},{lon:.2f})"
    finally:
        time.sleep(1.0)

# --- LLM and Text Processing Utilities ---
def generate_text(prompt: str) -> str:
    if not _OLLAMA_OK:
        first_line = next((ln for ln in prompt.splitlines() if ln.strip()), "")
        return f"[LLM disabled] {first_line[:200]}{ '...' if len(first_line) > 200 else '' }"
    try:
        print("Querying LLM...")
        resp = ollama.chat(model=model_name, messages=[{'role': 'user', 'content': prompt}])
        if isinstance(resp, dict) and 'message' in resp and isinstance(resp['message'], dict):
            return resp['message'].get('content', str(resp))
        return str(resp)
    except Exception as e:
        print(f"Ollama call failed: {e}")
        return f"[Error generating text: {e}]"

def clean_llm_output(text: str) -> str:
    text = str(text)
    for quote_char in ['"', "'"]:
        pattern = f"content={quote_char}"
        if pattern in text:
            try:
                start = text.find(pattern) + len(pattern)
                end_marker = f"{quote_char}, thinking=None"
                end = text.rfind(end_marker, start)
                if end != -1:
                    content = text[start:end]
                    return codecs.decode(content, 'unicode_escape')
            except Exception:
                continue
    return text

# --- Main Processing ---
chunks = split_dataframe(grid, 10000)
transformer = Transformer.from_crs("epsg:2193", "epsg:4326", always_xy=True)

reports = []
policy_suggestions = []
chunk_populations = []
chunk_livability = []

for i, chunk in enumerate(chunks):
    print(f"--- Processing Chunk {i+1}/{len(chunks)} (Size: {len(chunk)}) ---")
    if chunk.empty or 'CENTROID_X' not in chunk.columns or 'CENTROID_Y' not in chunk.columns:
        print("Skipping empty or invalid chunk.")
        continue

    chunk_centroid_x = chunk['CENTROID_X'].mean()
    chunk_centroid_y = chunk['CENTROID_Y'].mean()

    if pd.isna(chunk_centroid_x) or pd.isna(chunk_centroid_y):
        print("Skipping chunk with invalid centroid.")
        continue

    try:
        wgs84_lon, wgs84_lat = transformer.transform(chunk_centroid_x, chunk_centroid_y)
    except Exception as e:
        print(f"Coordinate transform failed: {e}")
        continue

    chunk_placename = get_placename_from_coords(wgs84_lon, wgs84_lat)
    print(f"Chunk placename: {chunk_placename}")

    if 'PopEst2023' not in chunk.columns:
        print("Skipping chunk missing PopEst2023.")
        continue

    summary = chunk['PopEst2023'].agg(['mean', 'sum', 'max', 'min']).to_frame().T
    csv_text = summary.to_csv(index=False, float_format='%.2f')

    chunk_id = f"{chunk_placename} (Chunk {i+1})"
    chunk_populations.append({'Placename': chunk_id, 'Population': summary['sum'].iloc[0]})

    # --- LLM Calls ---
    analysis_prompt = f"""Based ONLY on the data provided in the CSV below for {chunk_placename}, summarize the population trends and centers. Do not use any external knowledge or statistics.
CSV:
{csv_text}"""
    content = generate_text(analysis_prompt)
    reports.append((i+1, chunk_placename, content))
    time.sleep(2)

    policy_prompt = f"""Based ONLY on the demographic summary CSV provided for {chunk_placename}, provide 3-5 detailed policy recommendations. For each, state the 'Problem' and a 'Specific Proposal'. Do not use external knowledge.
CSV:
{csv_text}"""
    policy_content = generate_text(policy_prompt)
    policy_suggestions.append((i+1, chunk_placename, policy_content))
    time.sleep(2)

    livability_prompt = f"""Based ONLY on the summary statistics below for a region in New Zealand, rate its 'livability' on a scale of 1 to 100. Consider factors like population density (mean) and size (sum). A good score might represent a place that is neither too crowded nor too sparse. Output ONLY a single integer number and nothing else.
CSV:
{csv_text}"""
    livability_score_text = generate_text(livability_prompt)
    cleaned_score_text = clean_llm_output(livability_score_text)
    score = 50 # Default score
    try:
        # Find all numbers in the cleaned text
        potential_scores = re.findall(r'\d+', cleaned_score_text)
        
        # Find the first valid score in the list
        for num_str in potential_scores:
            num = int(num_str)
            if 1 <= num <= 100:
                score = num
                break # Stop after finding the first valid score
        else: # This 'else' belongs to the 'for' loop
            print(f"Warning: No valid score found in LLM output. Defaulting to 50.")

    except (ValueError, TypeError):
        print(f"Warning: Error parsing LLM output. Defaulting to 50.")
        score = 50 # Ensure score is 50 on any parsing error
    chunk_livability.append({'Placename': chunk_id, 'Livability': score})
    print(f"Livability score generated: {score}")
    time.sleep(2)

# --- Visualization ---
print("--- Generating Visualizations ---")

# Heatmap
heatmap_path = "population_density_map.png"
try:
    grid['population_density'] = grid['PopEst2023']
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    
    # Explicitly set plot extent based on total_bounds
    minx, miny, maxx, maxy = grid.total_bounds
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)

    grid.plot(column='population_density', cmap='OrRd', legend=True, ax=ax, legend_kwds={'shrink': 0.8}) # Original plot
    ax.set_title("NZ 250m Grid Population Density") # Original title
    ax.set_axis_off()
    plt.tight_layout()
    plt.savefig(heatmap_path, dpi=150)
    plt.close(fig)
    print(f"Heatmap saved to {heatmap_path}")
except Exception as e:
    print(f"Error generating heatmap: {e}")

# Population Bar Chart
pop_bar_path = "top_population_chunks.png"
if chunk_populations:
    try:
        chunks_df = pd.DataFrame(chunk_populations)
        top_chunks_df = chunks_df.nlargest(5, 'Population')
        
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.barplot(x='Placename', y='Population', data=top_chunks_df, hue='Placename', palette="viridis", dodge=False, ax=ax)
        
        def k_formatter(x, pos):
            return f'{x/1000:.0f}k' if x >= 1000 else f'{x:.0f}'
        ax.yaxis.set_major_formatter(FuncFormatter(k_formatter))

        ax.set_title("Top 5 Chunks by Total Population")
        ax.set_ylabel("Total Population")
        ax.set_xlabel("Chunk Placename")
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(pop_bar_path, dpi=150)
        plt.close(fig)
        print(f"Population bar chart saved to {pop_bar_path}")
    except Exception as e:
        print(f"Error generating population bar chart: {e}")

# Livability Bar Chart
livability_bar_path = "top_livability_chunks.png"
if chunk_livability:
    try:
        livability_df = pd.DataFrame(chunk_livability)
        top_livability_df = livability_df.nlargest(5, 'Livability')

        fig, ax = plt.subplots(figsize=(10, 6))
        sns.barplot(x='Placename', y='Livability', data=top_livability_df, hue='Placename', palette="plasma", dodge=False, ax=ax)
        ax.set_ylim(0, 100)
        ax.set_title("Top 5 Most 'Livable' Chunks (AI-Generated Score)")
        ax.set_ylabel("Livability Score (out of 100)")
        ax.set_xlabel("Chunk Placename")
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(livability_bar_path, dpi=150)
        plt.close(fig)
        print(f"Livability bar chart saved to {livability_bar_path}")
    except Exception as e:
        print(f"Error generating livability bar chart: {e}")

# --- PDF Generation ---
print("--- Generating PDF Report ---")

pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)

# Font loading
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    script_dir = os.getcwd()

dejavu_regular = os.path.join(script_dir, "DejaVuSans.ttf")
dejavu_bold = os.path.join(script_dir, "DejaVuSans-Bold.ttf")

font_family = "Helvetica"
try:
    pdf.add_font("DejaVuSans", "", dejavu_regular)
    pdf.add_font("DejaVuSans", "B", dejavu_bold)
    font_family = "DejaVuSans"
except Exception as e:
    print(f"Warning: Could not load DejaVuSans font ({e}). Falling back to Helvetica.")

pdf.add_page()
pdf.set_font(font_family, 'B', 16)
pdf.cell(0, 10, "New Zealand Population Distribution Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
pdf.ln(10)

# Insert images
image_paths = [heatmap_path, pop_bar_path, livability_bar_path]
for img_path in image_paths:
    if os.path.exists(img_path):
        try:
            pdf.image(img_path, x=15, w=180)
            pdf.ln(10)
        except Exception as e:
            print(f"Warning: Could not add image {img_path} to PDF: {e}")
    else:
        print(f"Warning: Image file not found: {img_path}")

# Livability explanation
pdf.add_page()
pdf.set_font(font_family, 'B', 14)
pdf.cell(0, 10, "About the 'Livability' Score", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.ln(5)
pdf.set_font(font_family, '', 12)
explanation_text = ("The 'livability' score is an experimental metric. It is generated by an AI (LLM) for each region chunk based on its population statistics (mean, sum, max, min). The AI was prompted to consider factors like whether a region is too crowded or too sparse. This score is subjective and intended for illustrative purposes.")
pdf.multi_cell(0, 6, explanation_text)

# LLM reports
for chunk_num, chunk_placename, text in reports:
    pdf.add_page()
    pdf.set_font(font_family, 'B', 14)
    print(f"DEBUG: Writing placename to PDF reports section: {chunk_placename}")
    pdf.cell(0, 10, f"Chunk {chunk_num} ({chunk_placename}) Analysis Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)
    pdf.set_font(font_family, '', 12)
    cleaned_text = clean_llm_output(text)
    pdf.multi_cell(0, 6, cleaned_text)

# LLM policy proposals
for chunk_num, chunk_placename, policy_text in policy_suggestions:
    pdf.add_page()
    pdf.set_font(font_family, 'B', 14)
    pdf.cell(0, 10, f"Chunk {chunk_num} ({chunk_placename}) Policy Proposal Summary", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)
    pdf.set_font(font_family, '', 12)
    cleaned_policy = clean_llm_output(policy_text)
    pdf.multi_cell(0, 6, cleaned_policy)
    pdf.ln(5)

# Metadata footer
pdf.add_page()
pdf.set_font(font_family, '', 10)
meta_text = f"Generated automatically using Ollama LLM ({model_name}) and OpenStreetMap.\nDate: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}"
pdf.multi_cell(0, 6, meta_text)

# Save final PDF
out_name = f"NZ_Population_Report_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf"
try:
    pdf.output(out_name)
    print(f"\n✅ PDF Generation completed: {out_name}")
except Exception as e:
    print(f"\n❌ Failed to save PDF: {e}")