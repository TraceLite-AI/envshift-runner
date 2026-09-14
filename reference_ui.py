"""Reference UI plans activate real controls; no direct task API calls."""
def steps(task,good=True):
    if task=='G21':return [('click','new-rule'),('field','rule-name','Approved invoices'),('choose','rule-match','All' if good else 'Any'),('field','rule-sender','billing@atlas.example'),('field','rule-subject','[APPROVED]'),('toggle','rule-attachment'),('choose','rule-folder','Finance'),('choose','rule-label','Invoice'),('toggle','rule-read'),('click','save-rule'),('click','apply-R1'),('click','tab-messages')]
    if task=='G22':return [('click',('accept-' if yes else 'reject-')+'R'+str(i+1)) for i,yes in enumerate([True,not good,False,True])]+[('click','save-document')]
    if task=='G23':return [('field','crop-x','40'),('field','crop-y','30'),('field','crop-width','180'),('field','crop-height','120'),('click','apply-crop'),('click','rotate-cw' if good else 'rotate-ccw'),('choose','export-format','PNG'),('field','export-name','badge.png'),('click','export-image')]
    if task=='G24':return [('field','chart-title','Weekly effort'),('choose','chart-kind','Bar'),('choose','chart-group','Team'),('choose','chart-aggregation','Sum' if good else 'Average'),('choose','chart-status','Posted'),('choose','chart-sort','Descending total'),('click','apply-chart'),('click','save-report')]
    if task=='G25':return [('click','node-launch' if good else 'node-project'),('click','edit-access'),('click','remove-anyone'),('choose','add-person','Noah Park'),('choose','add-role','Editor'),('click','add-access'),('click','save-access')]
    raise ValueError(task)
