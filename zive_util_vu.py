import numpy as np
import pandas as pd
import neurokit2 as nk
from bitstring import BitArray
import os, json, sys
from pathlib import Path


def zive_read_file_1ch(filename):
    f = open(filename, "r")
    a = np.fromfile(f, dtype=np.dtype('>i4'))
    ADCmax=0x800000
    Vref=2.5
    b = (a - ADCmax/2)*2*Vref/ADCmax/3.5*1000
    ecg_signal = b - np.mean(b)
    return ecg_signal

def zive_read_file_3ch(filename):
    f = open(filename, "r")
    a = np.fromfile(f, dtype=np.uint8)

    b = BitArray(bytes=a)
    d = np.array(b.unpack('intbe:32, intbe:24, intbe:24,' * int(len(a)/10)))
    # print (len(d))
    # printhex(d[-9:])

    ADCmax=0x800000
    Vref=2.5

    b = (d - ADCmax/2)*2*Vref/ADCmax/3.5*1000
    #b = d
    ch1 = b[0::3]
    ch2 = b[1::3]
    ch3 = b[2::3]
    start = 0#5000+35*200
    end = len(ch3)#start + 500*200
    ecg_signal = ch3[start:end]
    ecg_signal = ecg_signal - np.mean(ecg_signal)
    return ecg_signal

def runtime(s):
    hours, remainder = divmod(s, 3600)
    minutes, seconds = divmod(remainder, 60)
    print('Runtime: {:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds)))

def create_dir(parent_dir):
    """
    Sukuriami rekursyviškai aplankai, jei egzistuoja - tai nekuria
    https://smallbusiness.chron.com/make-folders-subfolders-python-38545.html
    Parameters
    ------------
        parent_dir: str
    """

    try:
        os.makedirs(parent_dir)
        print("Directory '%s' created successfully" % parent_dir)
        # print("Directory {:s} created successfully".format(parent_dir)
    except OSError as error:
        print("Directory '%s' already exists" % parent_dir)
def create_subdir(parent_dir, names_lst):
    # Sukuriami subdirektoriai su nurodytais pavadinimais
    for name in names_lst:
        # sukuriami aplankai EKG sekų vaizdams
        sub_dir = os.path.join(parent_dir, name)
        try:
            os.makedirs(sub_dir)
            print("Directory '%s' created successfully" % sub_dir)
        except OSError as error:
            print("Directory '%s' already exists" % sub_dir)

def get_rev_dictionary(dictionary):
    rev_dict = {value : key for (key, value) in dictionary.items()}
    return rev_dict

def get_freq_unique_values(y, cols_pattern=None):
  # y - numpy array
  # cols_pattern - pvz. ['N','S','V']
  (unique, counts) = np.unique(y, return_counts=True)
  if (cols_pattern is not None):
    return cols_pattern, counts, int(counts.sum())
  else:
    return unique, counts, int(counts.sum())


def get_recNr(rec_dir, userId, file_name):
    """
    Skriptas Zive ekg įrašo identikatoriams userId, file_name pakeisti į virtualią numeraciją:
    userId pakeičiamas į userNr - skaičiumi, pradedant nuo 1000, įrašo įdentifikatorius file_name pakeičiamas
    į įrašo eilės numerį registrationNr, lygų 0,1,... ir suformuojamas virtualus įrašo failo vardad SubjCode.
    Konversijai ir saugojimui panaudojamas df masyvas df_transl
    Jei paciento Nr nėra - užvedamas įrašas

    Perdarytas iš varianto, kuriame buvo naudojamas recordingID. Pakeistas į file_name
    """
    
    # Patikriname, ar df_transl egzistuoja. Jei ne, sukuriame ir įrašome pirmą įraša
    file_path = Path(rec_dir, 'df_transl.csv')
    if (not file_path.exists()):
        # Paruošiame masyvą - žodyną numerių vertimui iš userId, registrationId į userNr, registrationNr ir atgal
        # ir įrašome į diską
        first_rec = {'userId':[userId], 'file_name':[file_name], 'userNr':[1000], 'recordingNr':[0]}
        df_transl = pd.DataFrame(first_rec)
        file_path = Path(rec_dir, 'df_transl.csv')
        df_transl.to_csv(file_path)
        # print(df_transl)
        return df_transl.loc[0, 'userNr'], df_transl.loc[0, 'recordingNr']

    # Jei egzistuoja, nuskaitome vardų žodyną iš rec_dir aplanko
    file_path = Path(rec_dir, 'df_transl.csv')
    df_transl = pd.read_csv(file_path, index_col=0)
    # print(df_transl)
    # Ieškome, ar yra įrašas su userId
    # Jei userId nerandame, sukuriame naują įrašą su userId, recordingId, userNr, recordingNr 
    if (df_transl.loc[(df_transl['userId'] == userId)]).empty:
        userNr = df_transl['userNr'].max() + 1
        new_row = {'userId':userId, 'file_name':file_name, 'userNr':userNr, 'recordingNr':0}
        df_transl = df_transl.append(new_row, ignore_index=True)
        file_path = Path(rec_dir, 'df_transl.csv')
        df_transl.to_csv(file_path)
        return userNr, 0
    
    # Jei radus userId, randame kad šio paciento įrašo file_name jau yra, su įrašais nieko nedarome
    row = df_transl.loc[(df_transl['userId'] == userId) & (df_transl['file_name'] == file_name)]
    if not row.empty:
        # print(row)
        return row['userNr'].values[0], row['recordingNr'].values[0]
    else:
    # Jei šio paciento įrašo su file_name nėra, formuojame įrašą
        rows = df_transl.loc[(df_transl['userId'] == userId)]
        recordingNr = max(rows['recordingNr'].to_list()) + 1
        userNr = rows['userNr'].values[0]
        new_row = {'userId':userId, 'file_name':file_name, 'userNr':userNr, 'recordingNr':recordingNr}
        df_transl = df_transl.append(new_row, ignore_index=True)
        file_path = Path(rec_dir, 'df_transl.csv')
        df_transl.to_csv(file_path)
        return userNr, recordingNr    
    



def create_SubjCode(userNr, recordingNr):
    """
    Atnaujintas variantas, po to, kaip padaryti pakeitimai failų varduose 2022 03 26
    
    zive atveju: SubjCode = userNr + recordingNr, kur userNr >= 1000,
    pvz. SubjCode = 10001
    mit2zive atveju: SubjCode = userNr,  kur userNr < 1000,
    pvz. SubjCode = 101
    Parameters
    ------------
        userNr: int
        recordingNr: int
    Return
    -----------
        SubjCode : int
    """      
    # SubjCode = userNr + recordingNr
    # pvz. SubjCode = 10002
    if (userNr < 1000):
        return userNr
    else:        
        str_code = str(userNr) + str(recordingNr)   
        SubjCode = int(str_code)  
        return SubjCode


def split_SubjCode(SubjCode):
    """
    Atnaujintas variantas, po to, kaip padaryti pakeitimai failų varduose 2022 03 26
    
    zive atveju: SubjCode = int(str(userNr) + str(registrationNr)), kur userNr >= 1000,
    pvz. SubjCode = 10001
    mit2zive atveju: SubjCode = userNr,  kur userNr < 1000,
    pvz. SubjCode = 101
    https://www.adamsmith.haus/python/answers/how-to-get-the-part-of-a-string-before-a-specific-character-in-python
    Parameters
    ------------
        SubjCode: int
    Return
    -----------
        userNr: int
        recordingNr: int
    """   
    if (SubjCode < 1000):
        userNr = SubjCode
        recordingNr = 0   
        return userNr, recordingNr
    else:        
        str_code = str(SubjCode) 
        chars = list(str_code)
        str1 =""
        userNr = int(str1.join(chars[:4]))
        str2 =""
        recordingNr = int(str2.join(chars[4:]))
        return userNr, recordingNr
 
def get_userId(rec_dir, userNr):
    """
    Atnaujintas variantas, po to, kaip padaryti pakeitimai failų varduose 2022 03 26
    
    Užduotam paciento numeriui iš df_transl suranda ir gražina paciento userId
    Parameters
    ------------
        rec_dir: str
        userNr: int
    Return
    -----------
        userID: int
    """   
    # Patikriname, ar df_transl egzistuoja. 
    file = Path(rec_dir, 'df_transl.csv')
    if (file.exists()):
        # Nuskaitome vardų žodyną iš rec_dir aplanko
        file_path = Path(rec_dir, 'df_transl.csv')
        df_transl = pd.read_csv(file_path, index_col=0)
#       print(df_transl) 
         # Panaudodami df masyvą df_transl su įrašų numeriais iš įrašų eilės numerių gauname ZIVE userId
        row = df_transl.loc[(df_transl['userNr'] == userNr)]
        if row.empty:
            print("Klaida!")
            return None
        else:
            return row['userId'].values[0]
    else:
        print("df_transl neegzistuoja")


def get_beat_attributes(idx, all_beats_attr):
    # Atnaujintas variantas, po to, kaip padaryti pakeitimai failų varduose 2022 03 26 
    row = all_beats_attr.loc[idx]
    return row['userNr'], row['recordingNr'], row['label'], row['symbol'] 

def read_rec_attrib(rec_dir, SubjCode):
    # Pritaikyta nuskaityti json informaciją tiek mit2zive, tiek zive atvejams
    file_path = Path(rec_dir, str(SubjCode) + '.json')

    if (SubjCode > 1000): # zive atvejis
        with open(file_path,'r', encoding='UTF-8', errors = 'ignore') as f:
            data = json.loads(f.read())
        df = pd.json_normalize(data, record_path =['rpeaks'])
    else: # mit2zive atvejis
        df = pd.read_json(file_path, orient = 'records')

    atr_sample = df['sampleIndex'].to_numpy()
    atr_symbol = df['annotationValue'].to_numpy()
    return atr_sample, atr_symbol


def get_rec_Id(rec_dir, userNr, file_name):  #  netaisytas ////////////////////////
    # Patikriname, ar df_transl egzistuoja. 
    if (userNr < 1000):
         return userNr, None

    file = Path(rec_dir, 'df_transl.csv')
    if (file.exists()):
        # Nuskaitome vardų žodyną iš rec_dir aplanko
        file_path = Path(rec_dir, 'df_transl.csv')
        df_transl = pd.read_csv(file_path, index_col=0)
#       print(df_transl) 
         # Panaudodami df masyvą df_transl su įrašų numeriais iš įrašų eilės numerių gauname ZIVE numerius
        row = df_transl.loc[(df_transl['userNr'] == userNr)]
        if row.empty:
            print("Klaida!")
            return None, None
        else:
            userId = row['userId'].values[0]
            recordingId = None # reikia nuskaityti is json
            return userId, recordingId
    else:
        print("df_transl neegzistuoja")

def get_rec_userId(rec_dir, userNr):
    # Atnaujintas variantas, po to, kaip padaryti pakeitimai failų varduose 2022 03 26 
    
    # Patikriname, ar ne mit2zive
    if (userNr < 1000):
         return userNr
         
    # Patikriname, ar df_transl egzistuoja. 
    file = Path(rec_dir, 'df_transl.csv')
    if (file.exists()):
        # Nuskaitome vardų žodyną iš rec_dir aplanko
        file_path = Path(rec_dir, 'df_transl.csv')
        df_transl = pd.read_csv(file_path, index_col=0)
        #  print(df_transl) 
        # Panaudodami df masyvą df_transl su įrašų numeriais iš įrašų eilės numerių gauname ZIVE numerius
        row = df_transl.loc[(df_transl['userNr'] == userNr)]
        if row.empty:
            print("Klaida!")
            return None
        else:
            return row['userId'].values[0]
    else:
        print("df_transl neegzistuoja")

def read_rec(rec_dir, SubjCode):
    file_path = Path(rec_dir, str(SubjCode) + '.npy')
    signal = np.load(file_path, mmap_mode='r')
    # print(f"SubjCode: {SubjCode}  signal.shape: {signal.shape}")
    return signal
    
def zive_read_df_rpeaks(db_path, file_name):
    file_path = Path(db_path, file_name + '.json')
    with open(file_path,'r') as f:
        data = json.loads(f.read())
    df_rpeaks = pd.json_normalize(data, record_path =['rpeaks'])
    return df_rpeaks

def zive_read_df_data(file_path, name):
    df_data = pd.DataFrame()
    path = Path(file_path)
    # https://www.askpython.com/python-modules/check-if-file-exists-in-python
    if (path.exists()):
        with open(file_path,'r', encoding='UTF-8', errors = 'ignore') as f:
            data = json.loads(f.read())
        df_data = pd.json_normalize(data, record_path =[name])
    return df_data

def get_annotations_table(all_beats_attr, ind_lst=None, cols_pattern=None):

    """
    Atnaujintas variantas, po to, kaip padaryti pakeitimai failų varduose 2022 03 26

    Skaičiuoja anotacijų pasiskirstymą per pacientus ir jų įrašus
    ind_lst - indeksų sąrašas, kuriuos reikia įtraukti į skaičiavimą
    Parameters
    ------------
        all_beats_attr: dataframe
        ind_lst: list
        cols_pattern: list
    Return
    -----------
        labels_table: dataframe
        labels_sums: list
    """   

    if (ind_lst is not None):
        selected_beats_attr = all_beats_attr.loc[all_beats_attr.index[ind_lst]].copy()
    else:
        selected_beats_attr = all_beats_attr.copy()
    # print(selected_beats_attr)

    selected_beats_attr['SubjCodes'] =  selected_beats_attr['userNr'].astype(str) + selected_beats_attr['recordingNr'].astype(str)
    # print(selected_beats_attr)

    labels_table = pd.crosstab(index= selected_beats_attr['SubjCodes'], columns= selected_beats_attr['symbol'], margins=True)

    if (cols_pattern is not None):
        cols = list(labels_table.columns)
        cols_ordered = [s for s in cols_pattern if s in cols]
        labels_table = labels_table[cols_ordered]
    
    labels_sums = labels_table.sum(axis=1) 

    return labels_table, labels_sums


def print_annotations_table(labels_table, labels_sums, Flag1 = False, Flag2 = False):    
    if (Flag1):
        # išvęsti visą lentelę
        print(labels_table)
    else:    
        count = labels_table.loc['All']
        d = count.to_dict()
        print(str(d)[1:-1])

    if (Flag2):
        # išvęsti sumarinius rodiklius
        print("\n")
        print(labels_sums)
    else:
        print("Total: ", labels_sums.loc['All'])

def get_annotations_distribution(df_list, rec_dir, beats_annot):
    # Nustatomas anotacijų pasiskirstymas per visus įrašus.
    # Pasiruošimas ciklui per pacientų įrašus
    labels_rec_all = pd.DataFrame(columns=beats_annot.keys(),dtype=int)
    labels_rec_all.insert(0,"file_name",0)
    labels_rec_all = labels_rec_all.astype({"file_name":str})
    labels_rec_all.insert(1,"userId",0)
    labels_rec_all = labels_rec_all.astype({"userId":str})

    labels_rec = []

    # Ciklas per pacientų įrašus
    for ind in df_list.index:
        file_name = df_list.loc[ind, "file_name"]
        labels_rec = np.zeros(labels_rec_all.shape[1], dtype=int)
        file_name = df_list.loc[ind, "file_name"]

        #  load data using Python JSON module
        file_path = Path(rec_dir, file_name + '.json')
        with open(file_path,'r', encoding='UTF-8', errors = 'ignore') as f:
            data = json.loads(f.read())

        df_rpeaks = pd.json_normalize(data, record_path =['rpeaks'])

        atr_sample = df_rpeaks['sampleIndex'].to_numpy()
        atr_symbol = df_rpeaks['annotationValue'].to_numpy()

        # Ciklas per visas paciento įrašo anotacijas (simbolius)
        for symbol in atr_symbol:
            # Gaunamas anotacijos simbolio numeris anotacijų sąraše
            label = beats_annot.get(symbol)
            if (label == None):
                continue
            labels_rec[label] +=1

        # Sumuojame į bendrą masyvą
        dict = {'file_name':file_name, 'userId': data['userId'], 'N':labels_rec[0], 'S':labels_rec[1],
         'V':labels_rec[2], 'U':labels_rec[3]}
        labels_rec_all = labels_rec_all.append(dict, ignore_index = True)

    # Ciklo per pacientų įrašus pabaiga
    return labels_rec_all


def cm2df(cm, labels):
    df = pd.DataFrame()
    # rows
    for i, row_label in enumerate(labels):
        rowdata={}
        # columns
        for j, col_label in enumerate(labels): 
            rowdata[col_label]=cm[i,j]
        df = df.append(pd.DataFrame.from_dict({row_label:rowdata}, orient='index'))
    return df[labels]

def show_confusion_matrix(cnf_matrix, class_names):
    df = cm2df(cnf_matrix, class_names)
    print('Confusion Matrix')
    print(df)
    print("\n")

    flag_of_zero_values = False
    for i in range(len(class_names)):
        if (cnf_matrix[i,i] == 0):
            flag_of_zero_values = True

    if flag_of_zero_values != True:
        cnf_matrix_n = cnf_matrix.astype('float') / cnf_matrix.sum(axis=1)[:, np.newaxis]
        print('Normalized Confusion Matrix')
        df = cm2df(cnf_matrix_n, class_names)
        pd.options.display.float_format = "{:,.3f}".format
        print(df)
    else:
        print('Zero values! Cannot calculate Normalized Confusion Matrix')

def confusion_matrix_modified(y_true, y_pred, n_classes):
    cm = np.zeros((n_classes,n_classes), dtype=int)
    length = len(y_true)
    for i in range(length):
        cm[y_true[i],y_pred[i]] +=1
    return cm


