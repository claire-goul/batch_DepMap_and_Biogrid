import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import io
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize global variables
links_filtered = None
biogrid_df = None

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_correlations_edgelist(genes, links_filtered, threshold, corrpos, num):
    logger.info("Starting correlation analysis...")
    
    links_filtered_newfinal = pd.merge(links_filtered, genes, on=['Gene'])
    if corrpos:
        links_filtered_newfinal = links_filtered_newfinal[links_filtered_newfinal['corrscore'] >= threshold]
        grouped = links_filtered_newfinal.groupby('Gene')
        toplargestdf = pd.DataFrame()
        for var1, subdict in grouped:
            sub = subdict[subdict['corrscore'] > 0]
            sublargest = sub.nlargest(n=num, columns='corrscore')
            toplargestdf = pd.concat([toplargestdf, sublargest])
    else:
        links_filtered_newfinal = links_filtered_newfinal[links_filtered_newfinal['corrscore'] <= threshold]
        grouped = links_filtered_newfinal.groupby('Gene')
        toplargestdf = pd.DataFrame()
        for var1, subdict in grouped:
            sub = subdict[subdict['corrscore'] < 0]
            sublargest = sub.nlargest(n=num, columns='corrscore')
            toplargestdf = pd.concat([toplargestdf, sublargest])
            
    corr = (toplargestdf.reset_index()).drop(['index'], axis=1)
    logger.info(f"Correlation analysis complete. Found {len(corr)} correlations.")
    return corr

def get_biogrid_edgelist(genes, bg, filters, numcitations):
    logger.info("Processing BioGrid data...")
    
    def extract_gene_symbols(row, interactor='A'):
        symbols = set()
        
        # Extract from Aliases
        alias_col = f'Aliases Interactor {interactor}'
        if pd.notnull(row[alias_col]):
            aliases = str(row[alias_col]).split('|')
            for alias in aliases:
                if 'entrez gene/locuslink:' in alias.lower():
                    # Extract gene name before (gene name synonym)
                    gene = alias.split('(')[0].split(':')[-1].strip()
                    symbols.add(gene)
        
        # Extract from Alt IDs
        alt_id_col = f'Alt IDs Interactor {interactor}'
        if pd.notnull(row[alt_id_col]):
            alt_ids = str(row[alt_id_col]).split('|')
            for alt_id in alt_ids:
                if 'entrez gene/locuslink:' in alt_id.lower():
                    gene = alt_id.split('|')[0].split(':')[-1].strip()
                    symbols.add(gene)
        
        return list(symbols)

    # Create edge list
    edges = []
    genes_list = set(genes['Gene'].str.upper())
    
    logger.info(f"Processing {len(bg)} interactions...")
    
    # Process each interaction
    for _, row in bg.iterrows():
        genes_a = extract_gene_symbols(row, 'A')
        genes_b = extract_gene_symbols(row, 'B')
        
        # Check if any gene from A matches our genes of interest
        for gene_a in genes_a:
            if gene_a.upper() in genes_list:
                for gene_b in genes_b:
                    if gene_b.upper() != gene_a.upper():  # Avoid self-loops
                        edges.append((gene_a, gene_b))
        
        # Check if any gene from B matches our genes of interest
        for gene_b in genes_b:
            if gene_b.upper() in genes_list:
                for gene_a in genes_a:
                    if gene_a.upper() != gene_b.upper():  # Avoid self-loops
                        edges.append((gene_b, gene_a))
    
    logger.info(f"Found {len(edges)} potential interactions")
    
    # Convert to DataFrame
    if edges:
        edgelist_biogrid = pd.DataFrame(edges, columns=['Gene', 'Gene1'])
        
        # Count occurrences to filter by citation count
        edge_counts = edgelist_biogrid.groupby(['Gene', 'Gene1']).size().reset_index(name='count')
        edge_counts = edge_counts[edge_counts['count'] >= numcitations]
        
        # Create final edge list
        edgelist_biogrid_final = edge_counts.drop(columns=['count'])
        edgelist_biogrid_final['bg'] = 'yes'
        
        logger.info(f"Final interaction count: {len(edgelist_biogrid_final)}")
        return edgelist_biogrid_final
    else:
        return pd.DataFrame(columns=['Gene', 'Gene1', 'bg'])

@app.on_event("startup")
async def startup_event():
    """Load the large files when the server starts"""
    global links_filtered, biogrid_df
    
    try:
        # Load links file
        logger.info("Loading links file...")
        links_path = os.path.join('data', 'links_achilles.xlsx')
        if not os.path.exists(links_path):
            logger.error(f"Links file not found at {links_path}")
            raise FileNotFoundError(f"Links file not found at {links_path}")
        
        # Check file size
        file_size = os.path.getsize(links_path)
        logger.info(f"Links file size: {file_size} bytes")
        if file_size == 0:
            raise ValueError("Links file is empty")
            
        # Load with error checking
        try:
            links_filtered = pd.read_excel(
                links_path, 
                engine='openpyxl'
            )
            if links_filtered.empty:
                raise ValueError("Links file loaded but contains no data")
            logger.info(f"Links file loaded successfully: {len(links_filtered)} rows")
            logger.info(f"Links file columns: {list(links_filtered.columns)}")
        except Exception as e:
            logger.error(f"Error reading links file: {str(e)}")
            raise

        # Load BioGrid file
        logger.info("Loading BioGrid file...")
        biogrid_path = os.path.join('data', 'biogrid_human_processed_4_4_212.xlsx')
        if not os.path.exists(biogrid_path):
            logger.error(f"BioGrid file not found at {biogrid_path}")
            raise FileNotFoundError(f"BioGrid file not found at {biogrid_path}")
        
        # Check file size
        file_size = os.path.getsize(biogrid_path)
        logger.info(f"BioGrid file size: {file_size} bytes")
        if file_size == 0:
            raise ValueError("BioGrid file is empty")
            
        # Load with error checking
        try:
            biogrid_df = pd.read_excel(
                biogrid_path,
                engine='openpyxl'
            )
            if biogrid_df.empty:
                raise ValueError("BioGrid file loaded but contains no data")
            logger.info(f"BioGrid file loaded successfully: {len(biogrid_df)} rows")
            logger.info(f"BioGrid file columns: {list(biogrid_df.columns)}")
        except Exception as e:
            logger.error(f"Error reading BioGrid file: {str(e)}")
            raise

    except Exception as e:
        logger.error(f"Error loading files: {str(e)}")
        logger.error(f"Current working directory: {os.getcwd()}")
        logger.error(f"Files in current directory: {os.listdir()}")
        if os.path.exists('data'):
            logger.error(f"Files in data directory: {os.listdir('data')}")
        else:
            logger.error("Data directory not found")
        raise e

@app.get("/")
async def root():
    return {"message": "Gene Network API is running"}

@app.get("/status/")
async def get_status():
    """Get status of loaded files and additional information"""
    return {
        "links_file_loaded": links_filtered is not None,
        "biogrid_file_loaded": biogrid_df is not None,
        "links_file_rows": len(links_filtered) if links_filtered is not None else 0,
        "biogrid_file_rows": len(biogrid_df) if biogrid_df is not None else 0,
        "server_status": "running"
    }

@app.post("/upload/")
async def process_network(genes_file: UploadFile = File(...)):
    global links_filtered, biogrid_df
    
    # Check if required files are loaded
    if links_filtered is None or biogrid_df is None:
        raise HTTPException(
            status_code=503, 
            detail="Server is not ready. Required files are not loaded."
        )
    
    try:
        logger.info(f"Processing uploaded file: {genes_file.filename}")
        
        # Read the genes file
        genes_df = pd.read_excel(io.BytesIO(await genes_file.read()), engine='openpyxl')
        logger.info(f"Uploaded file contains {len(genes_df)} genes")

        # Process using pre-loaded data
        corr = get_correlations_edgelist(
            genes=genes_df,
            links_filtered=links_filtered,
            threshold=0.2,
            corrpos=True,
            num=3
        )

        edgelist_biogrid = get_biogrid_edgelist(
            genes=genes_df,
            bg=biogrid_df,
            filters=['psi-mi:"MI:0915"(physical association)'],
            numcitations=2
        )

        # Combine results
        corrwithbgforcorr = pd.merge(
            corr, 
            edgelist_biogrid,  
            how='left', 
            left_on=['Gene','Gene1'], 
            right_on=['Gene','Gene1']
        )
        logger.info(f"Combined results contain {len(corrwithbgforcorr)} interactions")

        # Convert to network format
        network_data = {
            "nodes": [],
            "edges": []
        }

        # Create unique node list
        unique_nodes = set()
        for _, row in corrwithbgforcorr.iterrows():
            unique_nodes.add(row['Gene'])
            unique_nodes.add(row['Gene1'])

        # Add nodes
        genes_list = set(genes_df['Gene'].tolist())
        network_data["nodes"] = [
            {"id": node, "isInterest": node in genes_list}
            for node in unique_nodes
        ]

        # Add edges
        network_data["edges"] = [
            {
                "source": row['Gene'],
                "target": row['Gene1'],
                "value": float(row['corrscore']) if 'corrscore' in row else 0,
                "isBiogrid": row.get('bg') == 'yes'
            }
            for _, row in corrwithbgforcorr.iterrows()
        ]

        logger.info(f"Network contains {len(network_data['nodes'])} nodes and {len(network_data['edges'])} edges")
        return network_data

    except Exception as e:
        logger.error(f"Error processing network: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
