class commitNode:
  def __init__(self,commit_msg,file_changes,timestamp,prev_commit=None):
    self.commit_msg = commit_msg
    self.file_changes = file_changes
    self.timestamp = timestamp
    self.prev_commit = prev_commit

class commitHistory:
  def __init__(self):
    self.head = None
  
  def add_commit(self,commit_msg,file_changes,timestamp):
    new_commit = commitNode(commit_msg,file_changes,timestamp,self.head)
    self.head = new_commit
    
  def get_commit_history(self):
    current_commit = self.head
    history = []
    while current_commit:
      history.append({
        'message': current_commit.commit_msg,
        'changes': current_commit.file_changes,
        'timestamp': current_commit.timestamp
      })
      current_commit = current_commit.prev_commit
    return history
  