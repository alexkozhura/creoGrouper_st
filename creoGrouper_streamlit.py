import pandas as pd
import os
import numpy as np
import streamlit as st
import zipfile
import shutil

def cleanup(temp_dir, archive_name):
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    if archive_name and os.path.exists(archive_name):
        os.remove(archive_name)

def process_file(uploaded_file):
    df = pd.read_csv(uploaded_file)
    df = df.replace('-', 0)
    cols = ['Spend', 'Installs', 'IPM',
        'eROAS D365 Forecast', 'RR D7 To-Date']
    for col in cols:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col])
    df = df.round(1)
    df['Base Creative Name'] = df['Creative (UA)'].str.extract(r'(^.*?)(?=_(\d+x\d+_\d+s|\d+s))')[0]
    df = df.drop(columns=['Creative (UA)'])

    group_col = 'Campaign (UA)' if 'Campaign (UA)' in df.columns else 'App'

    unique_values = df[group_col].unique()

    temp_dir = 'Results'
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    output_folder = temp_dir

    for value in unique_values:
        if value == 'Totals':
            break

        subset_df = df[df[group_col] == value]

        averaged_stats = subset_df.groupby('Base Creative Name').agg(
            Spend_sum = ('Spend', 'sum'),
            Installs_sum = ('Installs', 'sum'),
            IPM_w_avg = ('IPM', lambda x: np.average(df.loc[x.index, 'IPM'], weights=df.loc[x.index, 'Spend'])),
            eROAS_D365_w_avg = ('eROAS D365 Forecast', lambda x: np.average(df.loc[x.index, 'eROAS D365 Forecast'], weights=df.loc[x.index, 'Spend'])),
            RRD7_w_avg = ('RR D7 To-Date', lambda x: np.average(df.loc[x.index, 'RR D7 To-Date'], weights=df.loc[x.index, 'Spend']))
        ).sort_values(by='Spend_sum', ascending=False).reset_index().round(1)

        averaged_stats.to_csv(f'{output_folder}/{value}.csv', index=False)
    
    archive_name = f'{output_folder}.zip'
    with zipfile.ZipFile(archive_name, 'w') as archive:
        for foldername, subfolders, filenames in os.walk(output_folder):
            for filename in filenames:
                archive.write(os.path.join(foldername, filename))
    
    cleanup(output_folder, None)

    return archive_name


# Streamlit app main
st.title('Aggregate your creatives data by name (creo_9x5, creo_16x9 and creo_9x16 become creo)')
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    archive_name = process_file(uploaded_file)
    with open(archive_name, "rb") as f:
        bytes_data = f.read()
    st.write("Processing done. Download the results:")
    st.download_button(
        label="Download ZIP",
        data=bytes_data,
        file_name='Creos aggregated.zip',
        mime='application/zip'
    )

    os.remove(archive_name)
