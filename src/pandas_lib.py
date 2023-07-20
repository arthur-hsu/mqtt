import pandas as pd
import os, sys
import src.colorLog as log

def write(df, dict_tmp, columns):
    if df.empty==True:
        df = creat_df(columns = columns)
    # print(dict_tmp)
    new_data    = pd.DataFrame(data = dict_tmp, columns = columns, index=[0])
    df          = pd.concat([df, new_data], axis=0, ignore_index=True)
    # log.colo_prt('\t\t\t\tSHOW TABLE' , "BLUE", "WHITE",timestamp=0)
    # log.colo_prt('%s'%df , "BLUE", "WHITE",timestamp=0)
    return df
def creat_df(columns):
    log.Logger('[SYSTEM MSG] Create dataframe.' , 'BLUE', 'WHITE',0)
    df = pd.DataFrame(columns = columns)
    #print(df)
    return df
def save_to_excel(df,excel_writer,columns): 
    df.to_excel(
    excel_writer    = excel_writer,
    sheet_name      = 'RESULT',
    columns         = columns,
    index           = False,
    engine          = 'openpyxl'
    )
    excel_writer.save()
    log.Logger('[SYSTEM MSG] Dataframe save to excel.' , 'BLUE', 'WHITE')
