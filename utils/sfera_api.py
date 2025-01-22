import pickle


def generate_tasks(query):
    print(f"{query}")
    with open('tasks_dict_new.pickle', 'rb') as f:
        tasks = pickle.load(f)
    return tasks


def generate_tasks_test():
    with open('tasks_dict_new.pickle', 'rb') as f:
        tasks = pickle.load(f)
    return tasks
