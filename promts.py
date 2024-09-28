class Promt:


    params_dict = {"role" : ["system", "assistant", "user"], # Роль в промте
                    "is_open": ["open", "close"], # открытые вопросы или с вариантами ответов
                    "prof": ["Разработчик", "DevОps", "Сисадмин", "Аналитик", "Тестировщик", "Руководитель проекта"],
                    "section": ["Общие","fronted","backend", "full stack"],
                    "technology": ["Python", "C++", "C#", "Java", "Java Script", "1C", "Goland"], #потом добавлю и подумаю над структурой
                    "level": ["junior", "junior+", "middle", "middle+", "senior"],
                    "subtech": ["framework","lib","linked_tech"],
                    "num_questions":""           
                    }
    

   
    promt_path = {  ("system","open"): "promt_system_open.txt",
                    ("assistant","open"): "promt_assistant_open.txt",
                    ("user","open"): "promt_user_open.txt",
                    ("system","close"): "promt_system_close.txt",
                    ("assistant","close"): "promt_assistant_close.txt",
                    ("user","close"): "promt_user_open.txt"                  
                }
    
    replace_dict = {"Разработчик":"Программист, разработчик программного обеспечения на языке программирования",
                    "Аналитик":"аналитик, системный аналитик",
                    "Сисадмин": "системный админинистратор, системный инженер",
                    "Тестировщик":"тестировщик программного обеспечения, QA",
                    "open":"открытые вопросы",
                    "close":"закрытые вопросы с варианами ответов",
                    }
    
    add_dict = {"open": '''Вопрос должен проверять не набор справочных знаний, а выявлять понимание подходов к решению тех или иных задач.
Вопрос должен быть таким, чтобы ответ специалиста мог продемострировать его практический опыт.'''
                }
    
    
    def replace_str(self,param_value:str)-> str:
    #если существует значение (расшифровка) в словаре параметров берем его для подстановкив промт, если нет, подставляем ключ
        if param_value in Promt.replace_dict: 
            res = Promt.replace_dict[param_value] 
        else:
            res = param_value  # иначе в подстановку сохраняем значение ключа replace_dict, оно же value в params
        return res
    
    
    def get_base_promt(self, params:list):  #получить основной промт
    
        key_path = tuple(params[:2])
        promt_file_name = "Promts/"+Promt.promt_path[key_path]
        
        all_lists = []
        for lists in Promt.params_dict.values():  
            all_lists += lists  
        if len (all_lists) > len(set(all_lists)):  
            raise Exception ('Вcе значения  словаря  должны быть уникальными')
        
        if len (params) > len(set(params)):
            raise Exception ('Вcе значения параметров функции должны быть уникальными')
                    
        try:    
            with open (promt_file_name, 'r') as promt_file:
                promt_content = promt_file.read()
        except FileNotFoundError:
            print (f"Файл промта {promt_file_name} не найден")    
        
        for i, param_keys in enumerate(Promt.params_dict.keys()):
            param_value = params[i]  
            replace_str = self.replace_str(param_value)
            promt_content = promt_content.replace("{"+param_keys+"}", replace_str)
            
            if param_value in Promt.add_dict:
                promt_content += Promt.add_dict[param_value]

        promt_file.close()
        
        return promt_content
    
    def get_promt_ext(self, params, promt_history):  #получить доп промт
        return ""  