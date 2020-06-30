from spider import PaperSpider

paper_list = [
    # 'Mutual Relation Detection for Complex Question Answering over Knowledge Graph',
    # 'Leveraging Domain Context for Question Answering Over Knowledge Graph',
    'Towards Reliable Learning for High Stakes Applications',
    # 'Spot: Selecting Occupations from Trajectories',
    'GALLOP: GlobAL Feature Fused LOcation Prediction for Different Check-in Scenarios',
    # 'Community Level Diffusion Extraction'
]

spider = PaperSpider(paper_list, need_other_cited=True, need_cite_format=True)
spider.run()
