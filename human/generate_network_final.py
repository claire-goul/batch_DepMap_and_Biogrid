import pandas as pd
import numpy as np

#Written by Claire Goul -- Last Updated Oct 2023
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
def get_correlations_edgelist(genes,links_filtered,threshold,corrpos,num):
        links_filtered_newfinal=pd.merge(links_filtered, genes_of_interest,on=['Gene']) #filter by  genes of interest 
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
def get_biogrid_edgelist(genes,bg,filters,numcitations): 
        bg=bg.loc[bg['Taxid Interactor A']=='taxid:9606']
        bg=bg.loc[bg['Taxid Interactor B']=='taxid:9606']
        #bg=bg.reset_index()#FIRST GET ALL ALIASES OF BG GENES
        bg_df_final=bg
        bg_df_final=bg_df_final.reset_index()
        bg_df_final=bg_df_final[bg_df_final['Interaction Types']==filters[0]]
        bg_df_final=bg_df_final.reset_index()
        bg_df_final=bg_df_final.drop(columns=['index'])
        A=list(bg_df_final['Aliases Interactor A'])
        B=list(bg_df_final['Aliases Interactor B'])
        Anewog=[]
        Bnewog=[]
        Aog=list(bg_df_final['Alt IDs Interactor A'])
        Bog=list(bg_df_final['Alt IDs Interactor B'])
        for ele in range(0,len(Aog)):
                if len(Aog[ele])>1:
                        Aalts=[]
                        elesnewA=Aog[ele].split('|')
                        gene=elesnewA[1].split(':')[1].split('(')[0]
                        Aalts.append(gene)
                        Anewog.append(Aalts)
                else:
                        Anewog.append([])
        for ele in range(0,len(Bog)):
                if len(Bog[ele])>1:
                        Balts=[]
                        elesnewB=Bog[ele].split('|')
                        gene=elesnewB[1].split(':')[1].split('(')[0]
                        Balts.append(gene)
                        Bnewog.append(Balts)
                else:
                        Bnewog.append([])
        Anew=[]
        Bnew=[]
        for ele in range(0,len(A)):
                if len(A[ele])>1:
                        Aaliases=[]
                        elesnewA=A[ele].split('|')
                        for i in elesnewA:
                                gene=i.split(':')[1].split('(')[0]
                                Aaliases.append(gene)#add in aliases 
                        Aaliases.append(Anewog[ele][0]) #add in the original alt ID too
                        Anew.append(Aaliases)
                else:
                        Anew.append([])
        for ele in range(0,len(B)):
                if len(B[ele])>1:
                        Baliases=[]
                        elesnewB=B[ele].split('|')
                        for i in elesnewB:
                                gene=i.split(':')[1].split('(')[0]
                                Baliases.append(gene)
                        Baliases.append(Bnewog[ele][0])
                        Bnew.append(Baliases)
                else:
                        Bnew.append([])
        #then filter by genes of interest
        intAfin=[]
        intBfin=[]
        for gene in list(genes['Gene']):
                for a in range(0,len(Anew)):
                        if gene in Anew[a]:# this bg interaction is for a gene in genes of interest
                                intAfin.append(gene)
                                intBfin.append(Bnewog[a][0])#add corresponding B interactor (use the alias gene)
        for gene in list(genes['Gene']):
               for b in range(0,len(Bnew)):
                       if gene in Bnew[b]:# this bg interaction is for a gene in genes of interest
                               intAfin.append(gene)
                               intBfin.append(Anewog[b][0])#add corresponding A interactor (use the alias gene)
        edgelist_biogrid=pd.DataFrame()
        edgelist_biogrid['Final IDs Interactor A']=pd.DataFrame(intAfin)
        edgelist_biogrid['Final IDs Interactor B']=pd.DataFrame(intBfin)
        edgelist_biogrid['tuples']=list(zip(edgelist_biogrid['Final IDs Interactor A'],edgelist_biogrid['Final IDs Interactor B']))
        edgelist_biogrid=edgelist_biogrid.groupby('tuples').filter(lambda x : len(x)>=numcitations) #keep only genes that have more >= numcitations in biogrid
        edgelist_biogrid=edgelist_biogrid.reset_index()
        edgelist_biogrid=edgelist_biogrid.rename(columns={'Final IDs Interactor A':'Gene','Final IDs Interactor B':'Gene1'})
        genestuplesbiogrid=list(zip(edgelist_biogrid.Gene, edgelist_biogrid.Gene1))
        edgelist_biogrid=edgelist_biogrid.drop_duplicates(subset='tuples',keep='first')
        edgelist_biogrid=edgelist_biogrid.reset_index()
        edgelist_biogrid_final = edgelist_biogrid.drop(edgelist_biogrid[edgelist_biogrid.Gene==edgelist_biogrid.Gene1].index)
        edgelist_biogrid_final=edgelist_biogrid_final.drop(columns=['index'])
        edgelist_biogrid_final=edgelist_biogrid_final.reset_index()
        edgelist_biogrid_final['bg']='yes'
        return edgelist_biogrid_final

def merge3(list1, list2,list3):
    merged_list = [(list1[i], list2[i],list3[i]) for i in range(0, len(list1))]
    return merged_list



##LOAD IN BIOGRID DN DEPMAP DATA
links_filtered=pd.read_excel('links_achilles.xlsx')

bg=pd.read_csv('BIOGRID-ORGANISM-Homo_sapiens-4.4.212.csv')
genes_of_interest=pd.read_excel('NPC1_andNT__4_hitsneg.xlsx')## can read in any excel file to filter the correlation matrix by

#GET BIOGRID INTERACTIONS / COESSENTIAL GENES FOR GENES IN GENE LIST
corr=get_correlations_edgelist(genes_of_interest,links_filtered,threshold=0.2,corrpos='True',num=5)#if you want the coessential genes only for your gene list, just use this
edgelist_biogrid=get_biogrid_edgelist(genes_of_interest,bg,filters=['psi-mi:"MI:0915"(physical association)'],numcitations=2) #if you want the biogrid only for your gene list, just use this
edgelist_biogrid.to_excel('NPC1_andNT__4_hitsnegBG_2citations.xlsx')
corr.to_excel('NPC1_andNT__4_hitsnegcorr_0.2thresh_top5.xlsx')
corrwithbgforcorr = pd.merge(corr, edgelist_biogrid,  how='left', left_on=['Gene','Gene1'], right_on = ['Gene','Gene1'])
corrwithbgforcorr.to_excel('NPC1_andNT__4_hitsnegcorr_0.2thresh_top5_bg2minforcorr.xlsx')

#OPTIONS
#CORR: --GET CORR MATRIX FOR ALL GENES IN GENE LIST
#EDGELIST BIOGRID[0]: --BIOGRID INTERACTORS FOR ALL GENES IN GENE LIST
#IF YOU WANT NETWORK WITH BOTH, COMBINE BOTH EXCEL FILLES
#COMBINE: 1)COMBINE BIOGRID AND CORR INTO ONE NETWORK (GET BIOGRID INTERACTIONS ONLY FOR GENES IN GENE LIST). 2) GET BIOGRID INTERACTIONS FOR ALL CORR GENES AND ALL GENEES IN GENE LIST 
