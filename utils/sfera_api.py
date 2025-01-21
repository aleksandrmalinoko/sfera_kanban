import pickle


def generate_tasks():
    with open('tasks_dict.pickle', 'rb') as f:
        tasks = pickle.load(f)
    return tasks
