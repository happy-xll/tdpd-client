#!python
import click
import pandas as pd
from lib_tdpd import get_param_by_name, authorized_post

# command 入口
@click.command()
@click.option('--excel', '-e', default=None, help='请指定要导入的文件！')
def fun(excel):
    trans_data_to_tdpd(excel)

def trans_data_to_tdpd(f):
    #sheets =  ['passengerturnover']
    sheets =  ['freightturnover', 'passengerturnover']
    #f = '/opt/code/app/db/parav_middata/trans_data.xlsx'
    for sheet in sheets:
        df = pd.read_excel(f, sheet_name=sheet)
        #print(df)
        #df = df.drop(columns=['Type'])
        id_vars = ['year', 'month']
        dfc = df.melt(id_vars, var_name='fk_zone', value_name='v')
        param_info = get_param_by_name(sheet, 1)
        #dfc['fk_param'] = param_info.get('pk_param')
        #print(dfc)
        df_prov = pd.read_csv('./provinces.csv')
        df_prov = df_prov.rename(columns={'province':'fk_zone'})

        dfc = dfc.join(df_prov.set_index(['fk_zone']), on=['fk_zone'])

        dfu = dfc[['year', 'month', 'ad_prov', 'v']]
        dfu = dfu.rename(columns={'ad_prov': 'fk_zone'})
        dfs = dfu.pivot(index=['year', 'month'], columns='fk_zone', values='v').reset_index()
        print(dfs)
        data = dfs.to_dict(orient='split')
        #print(data)
        jdata = {
            'dataes': data,
            'param_name': sheet,
        }
        r = authorized_post('v1/param/{}/values'.format(param_info.get('pk_param')), jdata)

        print(r)
        #break


if __name__ == '__main__':
    fun()
