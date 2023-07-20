import pandas as pd
import os, time, sys, datetime
from styleframe import StyleFrame
import numpy as np
from openpyxl.utils import get_column_letter
import src.colorLog as log
# uplink_intv     = 180
# original_excel  = 'C:\\Users\\aaa89\\Desktop\\2023.04.07_162713-mqtt_report.xlsx'

class analysis_report():
    def __init__(self, uplink_intv, original_excel):
        self.uplink_intv        = uplink_intv
        self.original_excel     = original_excel
        self.original_df        = pd.read_excel(original_excel, sheet_name='RESULT')
        self.note_df            = pd.concat([self.original_df, pd.DataFrame(columns=['Note'])], sort=False)
        ## 行 dict ###############################################
        note_columns         = self.note_df.columns.to_list()
        self.columns_dict    = {}
        for col in note_columns:
            self.columns_dict['%s_index'%col]=note_columns.index(col)# 行 dict
        ## 列 dict ###############################################
        self.original_columns             = self.original_df.columns.to_list()
        self.data_dict, tmp_dict = {}, {}
        for col in self.original_columns:
            tmp_dict[col]=self.original_df[col]
            tmp_list=[]
            for value in tmp_dict[col]:
                tmp_list.append(value)
            self.data_dict[col]=tmp_list# 列dict
        ##########################################################
    
    def Write_Note(self):
        for index, row in self.note_df.iterrows():
            TimeMsg, FCntMsg= '',''
            current_time    = datetime.datetime.strptime((row[self.columns_dict['Time_index']]), '%Y-%m-%d %H:%M:%S')
            current_fcnt    = row[self.columns_dict['FCnt_index']]
            if index <len(self.note_df)-1:
                next_time = datetime.datetime.strptime(self.note_df.loc[index+1, 'Time'], '%Y-%m-%d %H:%M:%S')
                next_fcnt = self.note_df.loc[index+1, 'FCnt']

                #### FCnt ######################################
                time_diff = abs(next_time-current_time)
                if current_fcnt+1 != next_fcnt:
                    if current_fcnt+1 == next_fcnt-1 : Miss_FCnt = int(current_fcnt+1)
                    else : Miss_FCnt ='%s~%s'%(int(current_fcnt+1), int(next_fcnt-1))
                    FCntMsg ='Miss FCnt %s packet'%Miss_FCnt
                #### Time ######################################
                if time_diff> datetime.timedelta(seconds=self.uplink_intv*1.5):
                    # print('  %s %s\n- %s %s\n-------------------------\n=                 %s\n'%(next_fcnt, next_time, current_fcnt, current_time, time_diff))
                    TimeMsg = 'Haven\'t received data in %s'%time_diff
                ################################################

                if (TimeMsg or FCntMsg)!='':
                    self.note_df.loc[index+1, 'Note'] ='%s   %s'%(TimeMsg, FCntMsg)
        self.save_sheet(self.original_excel, 'RESULT', self.note_df)
        # print(self.note_df)

    def write_report(self, avg_list):
        avg_item_list=[]
        for item in avg_list:
            if item in self.original_columns:
                avg_item_list.append(item)
        avg_dict={}
        for key in avg_item_list:
            avg_item = sum(self.data_dict[key])/len(self.data_dict[key])
            # print('%s avg = %.1f'%(item, avg_item))
            avg_dict['%s avg'%key] = '%.1f'%avg_item
        report_df = pd.DataFrame(data=avg_dict, index=[0])
        # print(report_df)
        self.save_sheet(self.original_excel, 'REPORT', report_df)

    def save_sheet(self, path, sheet_name, df=''):
        with pd.ExcelWriter(path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False, index_label=False)
            #  计算每列表头的字符宽度
            column_widths = (df.columns.to_series().apply(lambda x: len(str(x).encode('gbk'))).values)
            #  计算每列的最大字符宽度
            max_widths = (df.astype(str).applymap(lambda x: len(str(x).encode('gbk'))).agg(max).values)
            # 取前两者中每列的最大宽度
            widths = np.max([column_widths, max_widths], axis=0)
            # 指定sheet，设置该sheet的每列列宽
            worksheet = writer.sheets[sheet_name]
            for i, width in enumerate(widths, 1):
                # openpyxl引擎设置字符宽度时会缩水0.5左右个字符，所以干脆+2使左右都空出一个字宽。
                worksheet.column_dimensions[get_column_letter(i)].width = width + 2
    def analysis(self, avg_list):
        print(avg_list)
        self.Write_Note()
        self.write_report(avg_list)
        log.Logger('[SYSTEM MSG] Analysis finished', 'BLUE','WHITE',timestamp=0)
