# Helper functions - Modelling stage

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pycountry
import pycountry_convert as pc


# Naive model

def apply_naive_prediction(train, test, target, lst_countries, country_var):
    y_pred = []  # Initialize y_pred as an empty list
    for c in lst_countries:
        train_c = train[train[country_var]==c]
        test_c = test[test[country_var]==c]

        y_pred_1 = train_c[target].iloc[-1]
        y_pred_2 = test_c[target].shift(1)  # Shift the values by 1 timestep
        y_pred_c = y_pred_2.fillna(y_pred_1)
        y_pred.append(y_pred_c)  # Append the predicted values to y_pred list

    return pd.concat(y_pred)  # Concatenate the predicted values into a single series or dataframe


# Multishift function with forward fill
def multi_shift_ffill(data, shift_cols, shift_range, country_var, year_var):
    shifted_data = [data.groupby(country_var)[shift_cols].shift(shift_value) for shift_value in range(shift_range.start, shift_range.stop)]
    shifted_df = pd.concat(shifted_data, axis=1, keys=[f'Shift_{shift_value}' for shift_value in range(shift_range.start, shift_range.stop)])
    an_index = data[[country_var, year_var]].copy()
    shifted_df.columns = shifted_df.columns.map(lambda col: '_'.join(col).strip())
    shifted_df = pd.concat([an_index, shifted_df], axis=1)
    tofill = shifted_df.groupby(country_var).first()
    shifted_df_filled = shifted_df.groupby(country_var).apply(lambda group: group.fillna(tofill.loc[group.name]))
    shifted_df_filled.reset_index(drop=True, inplace=True)
    
    return shifted_df_filled


# Rolling sums
def generate_rolling_sum_variables(data, group_cols, value_cols, window_sizes, date_col):
    panel_data = data.copy()
    panel_data = panel_data.sort_values(by=group_cols + [date_col])
    
    rolling_sums = [
        panel_data.groupby(group_cols)[value_col].transform(lambda x: x.rolling(window, min_periods=1).sum())
        .rename(f'rolling_sum_past_{window-1}_{value_col}')
        for value_col in value_cols
        for window in window_sizes
    ]
    
    panel_data = panel_data.join(pd.DataFrame(rolling_sums).transpose())
    
    return panel_data


## Continent mapping

def country_to_continent(iso3):
    if iso3 == 'UVK':
        return 'EU'
    elif iso3 =='TLS':
        return 'OC'
    elif iso3 =='WBG':
        return 'AS'

    country_alpha2 = pc.country_alpha3_to_country_alpha2(iso3)
    country_continent_code = pc.country_alpha2_to_continent_code(country_alpha2)
    return country_continent_code

def mapper(series, converter):
    unique_keys = series.drop_duplicates()
    unique_vals = unique_keys.apply(converter)
    mapper_dict = dict(zip(unique_keys, unique_vals))
    series = series.map(mapper_dict)
    series.name = series.name + '_continent'
    return series



## Test/Train split, 
def train_test_split(data, target_col, test_time_start, test_time_end, date_var):
    train = data.loc[data[date_var] < test_time_start]
    test = data.loc[(data[date_var] >= test_time_start) & (data[date_var] <= test_time_end)]
    
    X_train = train.drop(columns=target_col)
    y_train = train[target_col]
    
    X_test = test.drop(columns=target_col)
    y_test = test[target_col]
    
    return X_train, X_test, y_train, y_test

# Feature importance - graph with 20 main features
def feature_imp_more(feature_importances):
    imp = np.array(list(feature_importances.values()))
    names = list(feature_importances.keys())

    indexes = np.argsort(imp)[-21:]
    indexes = list(indexes)

    plt.barh(range(len(indexes)), imp[indexes], align='center')
    plt.yticks(range(len(indexes)), [names[i] for i in indexes])
    plt.show()

    return indexes


# Define a function to convert ISO2 to ISO3
def convert_iso2_to_iso3(iso2_code):
    try:
        country = pycountry.countries.get(alpha_2=iso2_code)
        return country.alpha_3
    except AttributeError:
        # ISO2 code not found
        return 'N/A'


from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer


## COSINE SIMILARITY FUNCTION

def cos_similarity(keywords_list, similarity_threshold):
        
    # Create a CountVectorizer object
    vectorizer = CountVectorizer()

    # Fit and transform the list of words
    word_vectors = vectorizer.fit_transform(keywords_list)

    # Calculate the cosine similarity matrix
    cosine_similarities = cosine_similarity(word_vectors)

    # Create an empty list to store the results
    results = []

    # Iterate over the words and their cosine similarities
    for i, word in enumerate(keywords_list):
        for j, other_word in enumerate(keywords_list):
            if i != j:
                similarity = cosine_similarities[i, j]
                results.append([word, other_word, similarity])

    # Create a DataFrame from the results list
    df_similarity = pd.DataFrame(results, columns=['Word 1', 'Word 2', 'Cosine Similarity'])

    # Create an empty list to store the column pairs and groups
   
    column_groups = []

    # Iterate over the rows in df_similarity
    for _, row in df_similarity.iterrows():
        word1 = row['Word 1']
        word2 = row['Word 2']
        similarity = row['Cosine Similarity']
        
        if similarity > similarity_threshold:
            found = False
            for group in column_groups:
                if word1 in group or word2 in group:
                    group.add(word1)
                    group.add(word2)
                    found = True
                    break
            if not found:
                column_groups.append({word1, word2})

    # Combine overlapping groups
    merged_groups = []
    for group in column_groups:
        merged = False
        for merged_group in merged_groups:
            if len(group.intersection(merged_group)) > 0:
                merged_group.update(group)
                merged = True
                break
        if not merged:
            merged_groups.append(group)

    # Convert groups to list
    column_groups = [list(group) for group in merged_groups]

    return column_groups
