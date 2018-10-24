
class Pagination(object):
    next_page = None
    prev_page = None
    current_page = None
    record_count = None
    total_pages = None
    set_size = 3
    next_set = []
    prev_set = []
    set_levels = {0:None}

    def calculate_sets(self):
        self.prev_set = []
        self.next_set = []

        if self.current_page > 1:
            self.prev_set = [self.current_page-i for i xrange(self.set_size) 
                             if self.current_page-i>0]

        if self.current_page < self.total_pages:
            self.next_set = [self.current_page+i for i xrange(self.set_size) 
                             if self.current_page+i<self.total]

        for sl in set_levels:
            if sl + 1:


'''
tens:

tens_gap = 20
number_of_links = 3

remainder = 10 - (page % 10)


lower
if current < (page+remainder) - 30
if current > (page+remainder) - (30 + number_of_links*10)
if current % 10 == 0
if current > 10

upper
remainder = 10 - (page % 10)
if current > page + 20
if current % 10 in 
    

'''
