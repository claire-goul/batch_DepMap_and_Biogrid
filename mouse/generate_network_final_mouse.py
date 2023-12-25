##Written by Claire Goul-- Updated Oct 2023
import pandas as pd
import numpy as np


##get_correlations_edgelist:
#INPUTS 
#genes: (excel file) with a column titled 'Gene' with list of genes of interest
#links_filtered (excel file) from generate_corrected_coessentiality downloaded from achilles website https://depmap.org/portal/download/all/
#threshold (float in range of 0-1), e.g. 0.2: number that correlation score has to be greater than
#corrpos (Boolean): if True, get only positive correlation genes; if false, get only negative corr genes
#num (int): number of correlated genes you want
#OUTPUT
#corr: correlation matrix with two columns, 'Gene' and 'Gene1' and their correlation scores ('corrscore')





#if you want negatively correlated genes, put threshold = "-0.2" or whatever cutoff
#issue1-- not all human genes in achilles were converted to mouse ortholog (various mouse genes in list are in human depmap, not in mouse depmap). never mind. this is because the gene it's correlated with isn't in depmap
def get_correlations_edgelist(genes,links_filtered,threshold,corrpos,num):
         #first filter by  genes of interest
        newgenes=[]
        newgenes1=[]
        newcorrscore=[]
        for gene in genes_of_interest['Gene']:# only thing might need to change-- if there are multiple aliases, and they aren't in genes, this just keeps the first one. ideally the aliases would match up with the biogrid aliases
                for entry in range(0,len(links_filtered['Gene'])):
                        if gene in links_filtered['Gene'][entry]:
                                newgenes.append(gene)
                                g1=links_filtered['Gene1'][entry]
                                g1new=g1.split("'")[1]
                                newgenes1.append(g1new)
                                newcorrscore.append(links_filtered['corrscore'][entry])               
                        elif gene in links_filtered['Gene1'][entry]:
                                newgenes1.append(gene)
                                g=links_filtered['Gene'][entry]
                                gnew=g.split("'")[1]
                                newgenes.append(gnew)
                                newcorrscore.append(links_filtered['corrscore'][entry])
        data=[newgenes,newgenes1,newcorrscore]
        links_new=pd.DataFrame(data).transpose()
        links_filtered_newfinal=links_new.rename(columns={0:'Gene',1:'Gene1',2:'corrscore'})
        links_filtered_newfinal['corrscore'] = pd.to_numeric(links_filtered_newfinal['corrscore'], errors='coerce')
        if corrpos:
                links_filtered_newfinal=links_filtered_newfinal[links_filtered_newfinal['corrscore']>=threshold]#threshold for degree of correlation
                grouped= links_filtered_newfinal.groupby('Gene')
                toplargestdf=pd.DataFrame()
                for var1,subdict in grouped:
                        sub=subdict[subdict['corrscore']>0]
                        sublargest=sub.nlargest(n=num,columns='corrscore') 
                        toplargestdf=pd.concat([toplargestdf,sublargest])
        else:
                links_filtered_newfinal=links_filtered_newfinal[links_filtered_newfinal['corrscore']<=threshold]#threshold for degree of correlation
                grouped= links_filtered_newfinal.groupby('Gene')
                toplargestdf=pd.DataFrame()
                for var1,subdict in grouped:
                        sub=subdict[subdict['corrscore']<0]
                        sublargest=sub.nlargest(n=num,columns='corrscore') 
                        toplargestdf=pd.concat([toplargestdf,sublargest])
        corr=(toplargestdf.reset_index()).drop(['index'],axis=1)
        return corr

##INPUTS
#genes: (excel file) with a column titled 'Gene' with list of genes of interest
#bg = csv file of all Biogrid interactors for human genes (downloaded from https://downloads.thebiogrid.org/BioGRID/Release-Archive/BIOGRID-4.4.220/ # BIOGRID-MV-Physical)
#filters:(list) of filters you want: either 'pull down', 'bioid', or both, or an empty list
##OUTPUT
#edgelist_biogrid: file with two columns of  biogrid interactions, 'InteractorA' and 'InteractorB' and 'tuples' column containing a tuple of those
#also make an option for biogrid only for corr and for hits only 
def get_biogrid_edgelist(genes,bg,numcitations): 
        #bg=bg.loc[bg['Taxid Interactor A']=='taxid:9606']
        #bg=bg.loc[bg['Taxid Interactor B']=='taxid:9606']
       # bg=bg.reset_index()#FIRST GET ALL ALIASES OF BG GENES
        bg_df_final=bg
        bg_df_final=bg_df_final.reset_index()
        bg_df_final=bg_df_final.reset_index()
        bg_df_final=bg_df_final.drop(columns=['index'])
        A=list(bg_df_final['OFFICIAL_SYMBOL_A'])
        B=list(bg_df_final['OFFICIAL_SYMBOL_B'])
        Aog=list(bg_df_final['ALIASES_FOR_A'])# currently this is aliases
        Bog=list(bg_df_final['ALIASES_FOR_B'])
        Anew=[]
        Bnew=[]
        for ele in range(0,len(A)):
                if type(Aog[ele])==str:
                        elesnewA=Aog[ele].split('|')
                        elesnewA.append(A[ele]) #add in the original alt ID too
                        Anew.append(elesnewA)
                else:
                        Anew.append([])
        for ele in range(0,len(B)):
                if type(Bog[ele])==str:
                        elesnewB=Bog[ele].split('|')
                        elesnewB.append(B[ele])
                        Bnew.append(elesnewB)
                else:
                        Bnew.append([])
        #then filter by genes of interest
        intAfin=[]
        intBfin=[]
        for a in range(0,len(Anew)):
                for gene in list(genes['Gene']):
                        if gene in Anew[a]:# this bg interaction is for a gene in genes of interest
                                intAfin.append(gene)
                                intBfin.append(Bnew[a][-1])#add corresponding B interactor (use the alias gene)
                                
        for b in range(0,len(Bnew)):
               for gene in list(genes['Gene']):
                       if gene in Bnew[b]:# this bg interaction is for a gene in genes of interest
                               test=b
                               intBfin.append(gene)
                               intAfin.append(Anew[b][-1])#add corresponding A interactor (use the alias gene)
        edgelist_biogrid=pd.DataFrame()
        edgelist_biogrid['Final IDs Interactor A']=pd.DataFrame(intAfin)
        edgelist_biogrid['Final IDs Interactor B']=pd.DataFrame(intBfin)
        edgelist_biogrid['tuples']=list(zip(edgelist_biogrid['Final IDs Interactor A'],edgelist_biogrid['Final IDs Interactor B']))
        edgelist_biogrid=edgelist_biogrid.groupby('tuples').filter(lambda x : len(x)>=numcitations) #keep only genes that have more >= numcitations in biogrid
        edgelist_biogrid=edgelist_biogrid.reset_index()
        edgelist_biogrid=edgelist_biogrid.rename(columns={'Final IDs Interactor A':'InteractorA','Final IDs Interactor B':'InteractorB'})
        genestuplesbiogrid=list(zip(edgelist_biogrid.InteractorA, edgelist_biogrid.InteractorB))
        edgelist_biogrid=edgelist_biogrid.drop_duplicates(subset='tuples',keep='first')
        edgelist_biogrid=edgelist_biogrid.reset_index()
        edgelist_biogrid_final = edgelist_biogrid.drop(edgelist_biogrid[edgelist_biogrid.InteractorA==edgelist_biogrid.InteractorB].index)
        edgelist_biogrid_final=edgelist_biogrid_final.drop(columns=['index'])
        edgelist_biogrid_final=edgelist_biogrid_final.reset_index()
        edgelist_biogrid_final['bg']='yes'
        return edgelist_biogrid_final

def merge3(list1, list2,list3):
    merged_list = [(list1[i], list2[i],list3[i]) for i in range(0, len(list1))]
    return merged_list



##LOAD IN BIOGRID DN DEPMAP DATA
links_filtered=pd.read_excel('links_achilles_mouse.xlsx')
bg=pd.read_excel('BIOGRID-ORGANISM_onlyMus_musculus-4.4.226_physical.xlsx')
#bg=pd.read_csv('BIOGRID-ORGANISM-Homo_sapiens-4.4.212.csv')
genes_of_interest=pd.read_excel('shared_pancreasliverlung.xlsx')## can read in any excel file to filter the correlation matrix by

#GET BIOGRID INTERACTIONS / COESSENTIAL GENES FOR GENES IN GENE LIST
#corr=get_correlations_edgelist(genes_of_interest,links_filtered,threshold=0.3,corrpos='True',num=3)#if you want the coessential genes only for your gene list, just use this
edgelist_biogrid=get_biogrid_edgelist(genes_of_interest,bg,numcitations=2) #if you want the biogrid only for your gene list, just use this
edgelist_biogrid.to_excel('shared_pancreasliverlung_biogrid_2ormorecitations.xlsx')
#corr.to_excel('shared_pancreasliverlung_Coessentiality_above.2_top3.xlsx')

#OPTIONS
#CORR: --GET CORR MATRIX FOR ALL GENES IN GENE LIST
#EDGELIST BIOGRID[0]: --BIOGRID INTERACTORS FOR ALL GENES IN GENE LIST
#IF YOU WANT NETWORK WITH BOTH, COMBINE BOTH EXCEL FILLES
#COMBINE: 1)COMBINE BIOGRID AND CORR INTO ONE NETWORK (GET BIOGRID INTERACTIONS ONLY FOR GENES IN GENE LIST). 2) GET BIOGRID INTERACTIONS FOR ALL CORR GENES AND ALL GENEES IN GENE LIST 
