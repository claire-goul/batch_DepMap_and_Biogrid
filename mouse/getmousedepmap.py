import pandas as pd
import numpy as np
## goal: convert depmap into mouse orthologs
#links_achilles: three columns- gene and gene1 and corrscore
##humantomouseorthologs_depmap: two columns (mappings)- gene_mouse and gene_human
links_filtered=pd.read_excel('links_achilles.xlsx')
mappings=pd.read_excel('huamntomouseorthologs_depmap.xlsx')

humangenes=list(mappings['Gene_human'])
mousegenes=list(mappings['Gene_mouse'])
tups=list(zip(mappings.Gene_mouse,mappings.Gene_human))


dicthumankeysmousevalues={k: list(v) for k,v in mappings.groupby("Gene_human")["Gene_mouse"]}
dfmappingsnew=pd.DataFrame.from_dict(dicthumankeysmousevalues,orient='index')
dfmappingsnew['combined']= dfmappingsnew.values.tolist()
newcol=[]
for listcomb in dfmappingsnew['combined']:
    res = [i for i in listcomb if i is not None]
    newcol.append(res)
dfmappingsnew['combinedfinal']= newcol
finaldf=dfmappingsnew['combinedfinal']
 finaldf.to_excel('huamntomouseorthologs_depmapfinal.xlsx')


#issure- because multiple entries for a given gene 
genesdepmap=list(links_filtered['Gene'])
genes1depmap=list(links_filtered['Gene1'])
finaldf=pd.read_excel('huamntomouseorthologs_depmapfinal.xlsx')

out = (links_filtered.merge(finaldf, left_on='Gene', right_on='Gene_human')
          .reindex(columns=['Gene', 'Gene1', 'corrscore', 'Genes_mouse']))



out1=(links_filtered.merge(finaldf, left_on='Gene1', right_on='Gene_human')
          .reindex(columns=['Gene', 'Gene1', 'corrscore', 'Genes_mouse']))
keys = ['Gene', 'Gene1']
intersection = out.merge(out1[keys], on=keys)

## alternate:
genes=pd.read_excel('allhumangenes_linksachilles.xlsx')
geneslist=list(genes['Gene'])
# find correct dataset name for your species
from pybiomart import Server
server = Server(host='http://www.ensembl.org')
server.marts['ENSEMBL_MART_ENSEMBL'].list_datasets()

from pyorthomap import FindOrthologs 
# then create the find orthogues object using correct datasets and attributes
# use help(FindOrthologs)
hs2mm = FindOrthologs(
          host = 'http://www.ensembl.org',
          mart = 'ENSEMBL_MART_ENSEMBL',
          from_dataset = 'hsapiens_gene_ensembl',
          to_dataset = 'mmusculus_gene_ensembl',
          from_filters = 'external_gene_name',
          from_values = geneslist,
          to_attributes = 'external_gene_name',
          to_homolog_attribute = 'mmusculus_homolog_ensembl_gene',
          from_gene_id_name = 'human_ensembl_gene_id',
          to_gene_id_name = 'mouse_ensembl_gene_id'
    )
    
hs2mm.map()
