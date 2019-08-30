'''
Created on Aug 28, 2019

@author: pjdrm
'''
from datetime import datetime
from tqdm import tqdm
import re

WOMEN = ',WOMEN,'
MEN = ',MEN,'
KIDS = ',KIDS,'
UNISEX = ',UNISEX,'

class Data(object):
    '''
    Class to load and pre-process files with query and product data.
    '''

    def __init__(self, products_data_path, query_data_path, max_samples=None):
        '''
        Constructor
        :param products_data_path: path to product file
        :param query_data_path: path to query file
        :param max_samples: maximum number of queries to process
        '''
        prod_info = self.process_products(products_data_path)
        query_sessions = self.process_queries(query_data_path,
                                              max_samples,
                                              prod_info)
    
    def process_products(self, products_data_path):
        '''
        Parses the products file to find the categories of the products.
        :param products_data_path: path to product file
        '''
        with open(products_data_path) as f:
            lins = f.readlines()[1:]
        
        prod_info = {}
        print('Loading products')
        for i in tqdm(range(len(lins))):
            lin = lins[i]
            #print(lin)
            if WOMEN in lin:
                gender = WOMEN
            elif MEN in lin:
                gender = MEN
            elif KIDS in lin:
                gender = KIDS
            elif UNISEX in lin:
                gender = UNISEX
            else:
                print('ERROR: unknown gender\n%s'%(lin))
                return -1
            
            prod_id = int(lin.split(',')[0])
            lin_split = lin.split(gender)[1].split(',')
            category1 = lin_split[1]
            category2 = lin_split[2]
            prod_info[prod_id] = {'gender': gender,
                                  'cat1': category1,
                                  'cat2': category2}
            #print(prod_info[prod_id])
        return prod_info
        
    def process_queries(self, query_data_path, max_samples, prod_info_dict):
        '''
        Parses a queries files to organize them by session.
        :param query_data_path: path to queries file
        :param max_samples: maximum number of queries to process
        :param prod_info_dict: information about product categories
        '''
        with open(query_data_path) as f:
            lins = f.readlines()[1:max_samples]
        
        total_samples = len(lins)-1
        if max_samples is None or max_samples > total_samples:
            max_samples = total_samples
        
        query_sessions = {}
        print('Loading queries')
        for i in tqdm(range(len(lins))):
            lin = lins[i]
            time_stamp,\
            session_id,\
            user_id,\
            search_query,\
            product_clicked,\
            product_id = lin.split(',')
            
            product_clicked = eval(product_clicked)
            session_id = int(session_id)
            prod_info = None
            if product_clicked:
                product_id = int(product_id)
                if product_id in prod_info_dict: #We might have the product
                    prod_info = prod_info_dict[product_id]
            
            if session_id not in query_sessions:
                query_sessions[session_id] = QuerySession(session_id,
                                                          search_query,
                                                          product_clicked,
                                                          product_id,
                                                          time_stamp,
                                                          prod_info)
            else:
                query_sessions[session_id].add_interaction(search_query,
                                                           product_clicked,
                                                           product_id,
                                                           time_stamp,
                                                           prod_info)
        #Mainly for understanding the data better
        n_rephrases = 0
        with open('rephrase_queries.txt', 'w+') as f:
            for id in query_sessions:
                q_session = query_sessions[id]
                q_session.check_query_rephrase()
                q_session.add_product_to_rephrase()
                #print('has_rephrase_q: %s\n%s' % (str(q_session.has_rephrase_q), q_session))
                if q_session.has_rephrase_q:
                    f.write(str(query_sessions[id])+'\n')
                    n_rephrases += len(q_session.rephrase_seqs)
        print('Total rephrase queries: %d' % n_rephrases)
        return query_sessions
                
class QuerySession(object):
    '''
    Class that aggregates queries from the same session.
    '''

    def __init__(self, session_id,
                       search_query,
                       product_clicked,
                       product_id,
                       time_stamp,
                       prod_info):
        '''
        Constructor
        :param session_id: session identifier
        :param search_query: query enter by user
        :param product_clicked: if the user clicked on any product result
        :param product_id: idetifier of the clicked produt
        :param time_stamp: time query was entered
        :param prod_info: product categories
        '''
        self.session_id = session_id
        self.queries = [search_query]
        self.clicks = [product_clicked]
        self.products = [product_id]
        self.time_stamps = [datetime.strptime(time_stamp.split('.')[0],
                           '%Y-%m-%d %H:%M:%S')]
        self.prods_info = [prod_info]
        self.has_rephrase_q = None
        self.rephrase_seqs = []
        
    def __str__(self):
        q_str = ''
        i = 0
        for q, click, time_stamp in zip(self.queries,
                                        self.clicks,
                                        self.time_stamps):
            if i == 0:
                time_diff = '-1'
            else:
                time_diff = time_stamp-self.time_stamps[i-1]
                time_diff = str(time_diff.total_seconds())
            q_str += q+' ('+str(click)+' '+time_diff+')'+'| '
            i += 1
        q_str += '\n'
        for i, j in self.rephrase_seqs:
            for q in range(i, j+1):
                q_str += self.queries[q]+' -> '
            q_str = q_str[:-4]+'| '
        return q_str
        
    def add_interaction(self,
                        search_query,
                        product_clicked,
                        product_id,
                        time_stamp,
                        prod_info):
        '''
        Adds a new query made in a session.
        :param search_query: query enter by user
        :param product_clicked: if the user clicked on any product result
        :param product_id: idetifier of the clicked produt
        :param time_stamp: time query was entered
        :param prod_info: product categories
        '''
        self.queries.append(search_query)
        self.clicks.append(product_clicked)
        self.products.append(product_id)
        self.time_stamps.append(datetime.strptime(time_stamp.split('.')[0],
                                '%Y-%m-%d %H:%M:%S'))
        self.prods_info.append(prod_info)
        
    def check_query_rephrase(self):
        '''
        Determines if a sequence of queries contains a rephrase. A rephrase
        is a sequence of queries started with a no click and ending with another
        query with a click.
        '''
        self.has_rephrase_q = False
        started_rephrase = False
        bl_queries = {} #sometimes there is a sequence with equal queries without clicks
        i = 0
        begin_rephrase = -1
        for query, click in zip(self.queries, self.clicks):
            if query in bl_queries:
                started_rephrase = False
            elif not click and not started_rephrase:
                started_rephrase = True
                begin_rephrase = i
            elif click and started_rephrase:
                self.has_rephrase_q = True
                self.rephrase_seqs.append([begin_rephrase, i])
                begin_rephrase = -1
                started_rephrase = False
            bl_queries[query] = True
            i += 1
    
    def add_product_to_rephrase(self):
        '''
        Adds the products to queries before the final rephrased query.
        This can be done since the rephrased has a o product click.
        '''
        for i, j in self.rephrase_seqs:
            for q in range(i, j):
                self.prods_info[q] = self.prods_info[j] #the last query of a rephrase has a product
                        
Data('/home/pjdrm/Downloads/products.csv',
     '/home/pjdrm/Downloads/queries_sample.csv',
     max_samples=None)

