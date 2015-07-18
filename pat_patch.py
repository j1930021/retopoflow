'''
Created on Jul 15, 2015

@author: Patrick
'''
from pulp import LpVariable, LpProblem, LpMinimize, LpMaximize, LpInteger, LpStatus

def permute_subdivs(L):
    '''
    returns a list of permutations that preserves the original
    list order of the sides going CW and CCW around the loop
    
    return:
       permutations - lsit of lists
       shift_rev - list of tupple (k, rev) k represents the index
       in the orignial list which is now the 0th element in the
       permutation.
    '''
    perms = []
    shift_dir = []
    N = len(L)
    for i in range(0, N -1):
        p = L[i:] + L[:i]
        perms += [p]
        shift_dir += [(i, 1)]
        pr = p.copy()
        pr.reverse()
        perms += [pr]
        shift_dir += [((i+N-1) % N, -1)]
    
    return perms, shift_dir
    
def reducible(edge_subdivs):
    '''
    see section 2.1 in the paper #TODO paper reference    
    '''
    N = len(edge_subdivs)
    reducible_ks = []
    reduction_ds = []
    reduction_potientials = []
    
    for k, l in enumerate(edge_subdivs):
        k_min_1 = (k - 1) % N
        k_plu_1 = (k + 1) % N
        
        l_k = edge_subdivs[k]
        l_k_min_1 = edge_subdivs[k_min_1]
        l_k_plu_1 = edge_subdivs[k_plu_1]

        if l_k_min_1 > 1 and l_k_plu_1 > 1:
            d = min(l_k_min_1, l_k_plu_1) - 1
            reducible_ks += [k]
            reduction_ds += [d]
            reduction_potientials += [d * l_k]

        
    return reducible_ks, reduction_ds, reduction_potientials
    
    
def reduce_edges(edge_subdivs, k, d):
    '''
    list of edge subdivisions
    k  - side to reduce on
    d - amount to reduce by
    '''
    N = len(edge_subdivs)
    new_subdivs = []
    k_min_1 = (k - 1) % N
    k_plu_1 = (k + 1) % N
            
    for i in range(0,N):
        
        if i == k_min_1 or i == k_plu_1:
            new_subdivs.append(edge_subdivs[i] - d)
        else:
            new_subdivs.append(edge_subdivs[i])
            
    return new_subdivs
    
class Patch():
    def __init__(self):
        
        self.valid = False
        self.corners = []  #list of vectors representing locations of corners
        self.edge_subdivision = []  # a list of integers representingthe segments of each side.  l0.....lN-1
        self.pattern = 0  #fundamental pattern

        self.reductions = {}
        self.edges_reduced = []
        
    def validate(self):
        self.valid = False
        self.valid |= len(self.corner) == len(self.sides)
        self.valid |= (sum(self.edge_subdivision) % 2) == 0  #even subdiv
        
        return self.valid
        
    def permute_and_find_solutions(self):
        
        pat_dict = {}
        pat_dict[3] = 2
        pat_dict[4] = 5
        pat_dict[5] = 4
        pat_dict[6] = 4
        
        perms, rot_dirs = permute_subdivs(self.edge_subdivision)
        
        valid_perms = []
        valid_rot_dirs = []
        valid_patterns = []
        valid_solutions = []
        N = len(self.edge_subdivision)
        
        for i, perm in enumerate(perms):
            for pat in range(0,pat_dict[N]):
                if N == 6:
                    sol = PatchSolver6(perm, pat)
                elif N == 5:
                    sol = PatchSolver5(perm, pat)
                elif N == 4:    
                    sol = PatchSolver4(perm, pat)
                elif N == 3:    
                    sol = PatchSolver3(perm, pat)
                    
                sol.solve()
              
    def reduce_input_cornered(self):
        '''
        slices off the biggest quad patches it can at a time
        this is not needed for patch solving, just proves
        generality of the approach
        '''
        
        edge_subdivs = self.edge_subdivision.copy()
        print('\n')
        print('Reduction series for edges')
        print(edge_subdivs)
        ks, ds, pots = reducible(edge_subdivs)
        
        if not len(ks):
            print('already maximally reduced')
            self.edges_reduced = edge_subdivs
            return
        
        
        iters = 0
        while len(ks) and iters < 10:
            iters += 1
            best = pots.index(max(pots))
            new_subdivs = reduce_edges(edge_subdivs, ks[best], ds[best])
            
            ks, ds, pots = reducible(new_subdivs)
            print(new_subdivs)
            edge_subdivs = new_subdivs
         
        self.edges_reduced = new_subdivs
    
    def reduce_input_centered(self):
        '''
        slices off the smallest quad patches it can at a time

        this is not needed for patch solving, just proves
        generality of the approach
        '''
        
        edge_subdivs = self.edge_subdivision.copy()
        ks, ds, pots = reducible(edge_subdivs)
        print(edge_subdivs)
        if not len(ks):
            print('maximally reduced')
            return
        iters = 0
        while len(ks) and iters < 10:
            iters += 1
            best = pots.index(min(pots))
            new_subdivs = reduce_edges(edge_subdivs, ks[best], ds[best])
            
            
            ks, ds, pots = reducible(new_subdivs)
            print(new_subdivs)
            edge_subdivs = new_subdivs
        
        print('centered reduced in %i iters' % iters)
   
        self.edges_reduced = new_subdivs
    
    def reduce_input_padding(self):
        '''
        slices 1 strip off the biggest quad patches it can at a time
        this is not needed for patch solving, just proves
        generality of the approach
        '''
        
        edge_subdivs = self.edge_subdivision.copy()
        print('\n')
        print('Reduction series for edges')
        print(edge_subdivs)
        ks, ds, pots = reducible(edge_subdivs)
        
        if not len(ks):
            print('already maximally reduced')
            self.edges_reduced = edge_subdivs
            return
        
        iters = 0
        while len(ks) and iters < 10:
            iters += 1
            best = pots.index(max(pots))
            new_subdivs = reduce_edges(edge_subdivs, ks[best], 1)
            
            ks, ds, pots = reducible(new_subdivs)
            print(new_subdivs)
            edge_subdivs = new_subdivs
         
        self.edges_reduced = new_subdivs
            
    def identify_patch_pattern(self):   
        n_sides = len(self.edges_reduced)
        unique = set(self.edges_reduced)
        alpha = max(unique)
        beta = None
        x = None
        
        if len(self.edge_subdivision) == 3:
            if alpha == 2:
                self.pattern = 0
            else:
                self.pattern = 1
                x = (alpha - 4)/2
                
        elif len(self.edge_subdivision) == 4:
            if alpha == 1:
                self.pattern = 0
                
            elif len(unique) == 2 and self.edges_reduced.count(alpha) == 1:
                #there is only one alp
                x = (alpha - 3) / 2
                if x == 0:
                    self.pattern = 2
                    print('[A,1,1,1] and x = 0, need to parameterize y?')
                else:
                    print('[A,1,1,1] and A = 3 + 2x   REally unsure on these!')
                    self.pattern = 3
                    
            elif len(unique) == 2 and self.edges_reduced.count(alpha) == 2:
                self.pattern = 1
                print('[A,B,1,1] and A = B -> [A,A,1,1]')
                
               
            elif len(unique) == 3:
                self.pattern = 4
                print('[A,B,1,1]  A = B + 2 + 2x')
                beta = (unique - set([1,alpha])).pop()
                
                       
        elif len(self.edge_subdivision) == 5:
            if len(unique) == 2 and alpha ==2:
                self.pattern = 0
                print('[A,1,1,1,1] and A = 2')
                    
            elif len(unique) == 2 and alpha > 2:
                self.pattern = 2
                print('[A,1,1,1,1] and A = 4 + 2x')
                    
            elif len(unique) == 3:
                beta = (unique - set([1,alpha])).pop()
                if beta == alpha -1:
                    self.pattern = 1
                    print('[A,B,1,1,1] and A = B + 1')
                else:
                    self.pattern = 3
                    print('[A,B,1,1,1] and A = B + 3 + 2x')
                    
                                   
        elif len(self.edge_subdivision) == 6:
            
            if len(unique) == 1:
                self.pattern = 0
                print('[1,1,1,1,1,1] parameter x = 0')
                
            elif len(unique) == 2 and self.edges_reduced.count(alpha) == 1:
                self.pattern = 2
                print('[A,1,1,1,1,1] parameter y = 0')
                
            elif len(unique) == 2 and self.edges_reduced.count(alpha) == 2:
                k = self.edges_reduced.index(alpha)
                k_plu1 = (k + 1) % n_sides
                k_min1 = (k - 1) % n_sides
                
                if self.edges_reduced[k_plu1] == alpha or self.edges_reduced[k_min1] == alpha:
                    self.pattern = 1
                    print('[A,B,1,1,1,1] and A = B -> [A,A,1,1,1,1]')
                else:
                    self.pattern = 0
                    print('[A,1,1,B,1,1] and A = B ->  [A,1,1,A,1,1]')
                    
                
            elif len(unique) == 3:
                k = self.edges_reduced.index(alpha)
                k_plu1 = (k + 1) % 6
                k_min1 = (k - 1) % 6
                beta = (unique - set([1,alpha])).pop()
                if self.edges_reduced[k_plu1] == beta or self.edges_reduced[k_min1] == beta:
                    self.pattern = 3
                    print('[A,B,1,1,1,1] and A = B + 2 + 2x')
                else:
                    self.pattern = 2
                    print('[A,1,1,B,1,1] and A = B + 2 + 2x')
                    
        else:
            print('bad patch!')
            
        print('Alpha = %i' % alpha)
        print('Beta = %s' % str(beta))
        print('%i sided patch with pattern #%i' % (n_sides, self.pattern))
        k0 = self.edges_reduced.index(alpha)
        print('l_0  side is side #%i, value %i' % (k0, self.edges[k0]))


def add_constraints_3p0(prob, L, p0, p1, p2):  #DONE
    prob +=  p2 + p1            == L[0] - 2, "Side 0"
    prob +=  p0 + p2            == L[1] - 1, "Side 1"
    prob +=  p1 + p0            == L[2] - 1, "Side 2"
    
def add_constraints_3p1(prob, L, p0, p1, p2, x):     #DONE
    prob +=  p2 + p1 +2*x       == L[0] - 4, "Side 0"
    prob +=  p0 + p2            == L[1] - 1, "Side 1"
    prob +=  p1 + p0            == L[2] - 1, "Side 2"

def add_constraints_4p0(prob, L, p0, p1, p2, p3):     #DONE
    prob +=  p3 + p1            == L[0] - 1, "Side 0"
    prob +=  p0 + p2            == L[1] - 1, "Side 1"
    prob +=  p1 + p3            == L[2] - 1, "Side 2"
    prob +=  p2 + p0            == L[3] - 1, "Side 3"

def add_constraints_4p1(prob, L, p0, p1, p2, p3, x):   #DONE
    prob +=  p3 + p1 + x        == L[0] - 2, "Side 0"
    prob +=  p0 + p2 + x        == L[1] - 2, "Side 1"
    prob +=  p1 + p3            == L[2] - 1, "Side 2"
    prob +=  p2 + p0            == L[3] - 1, "Side 3"
    
def add_constraints_4p2(prob, L, p0, p1, p2, p3, x, y):   #DONE
    prob +=  p3 + p1 + x + y    == L[0] - 3, "Side 0"
    prob +=  p0 + p2 + x        == L[1] - 1, "Side 1"
    prob +=  p1 + p3            == L[2] - 1, "Side 2"
    prob +=  p2 + p3 + y        == L[3] - 1, "Side 3"


def add_constraints_4p3(prob, L, p0, p1, p2, p3, x):   #DONE
    prob +=  p3 + p1 + 2*x      == L[0] - 3, "Side 0"
    prob +=  p0 + p2            == L[1] - 1, "Side 1"
    prob +=  p1 + p3            == L[2] - 1, "Side 2"
    prob +=  p2 + p0            == L[3] - 1, "Side 3"

    
def add_constraints_4p4(prob, L, p0, p1, p2, p3, x, y):   #DONE
    prob +=  p1 + p1 + 2*x + y  == L[0] - 4, "Side 0"
    prob +=  p0 + p2 + y        == L[1] - 2, "Side 1"
    prob +=  p1 + p3            == L[2] - 1, "Side 2"
    prob +=  p2 + p0            == L[3] - 1, "Side 3"

def add_constraints_5p0(prob, L, p0, p1, p2, p3, p4):   #DONE
    prob +=  p4 + p1            == L[0] - 2, "Side 0"
    prob +=  p0 + p2            == L[1] - 1, "Side 1"
    prob +=  p1 + p3            == L[2] - 1, "Side 2"
    prob +=  p2 + p4            == L[3] - 1, "Side 3"
    prob +=  p3 + p0            == L[4] - 1, "Side 4"

    
def add_constraints_5p1(prob, L, p0, p1, p2, p3, p4, x): #DONE
    prob +=  p4 + p1 + x        == L[0] - 2, "Side 0"
    prob +=  p0 + p2 + x        == L[1] - 1, "Side 1"
    prob +=  p1 + p3            == L[2] - 1, "Side 2"
    prob +=  p2 + p4            == L[3] - 1, "Side 3"
    prob +=  p3 + p0            == L[4] - 1, "Side 4"

    
def add_constraints_5p2(prob, L, p0, p1, p2, p3, p4, x): #DONE
    prob +=  p4 + p1 + 2*x      == L[0] - 4, "Side 0"
    prob +=  p0 + p2            == L[1] - 1, "Side 1"
    prob +=  p1 + p3            == L[2] - 1, "Side 2"
    prob +=  p2 + p4            == L[3] - 1, "Side 3"
    prob +=  p3 + p0            == L[4] - 1, "Side 4"

    
def add_constraints_5p3(prob, L, p0, p1, p2, p3, p4, x, y): #DONE
    prob +=  p4 + p1 + 2*x + y  == L[0] - 5, "Side 0"
    prob +=  p0 + p2 + y        == L[1] - 2, "Side 1"
    prob +=  p1 + p3            == L[2] - 1, "Side 2"
    prob +=  p2 + p4            == L[3] - 1, "Side 3"
    prob +=  p3 + p0            == L[4] - 1, "Side 4"

                
def add_constraints_6p0(prob, L, p0, p1, p2, p3, p4, p5, x): #Done
    prob +=  p5 + p1 + x        == L[0] - 1, "Side 0"
    prob +=  p0 + p2            == L[1] - 1, "Side 1"
    prob +=  p1 + p3            == L[2] - 1, "Side 2"
    prob +=  p2 + p4 + x        == L[3] - 1, "Side 3"
    prob +=  p3 + p5            == L[4] - 1, "Side 4"
    prob +=  p4 + p0            == L[5] - 1, "Side 5"
    
def add_constraints_6p1(prob, L, p0, p1, p2, p3, p4, p5, x): #DONE
    prob +=  p5 + p1 + x       == L[0] - 2, "Side 0"
    prob +=  p0 + p2 + x        == L[1] - 2, "Side 1"
    prob +=  p1 + p3            == L[2] - 1, "Side 2"
    prob +=  p2 + p4            == L[3] - 1, "Side 3"
    prob +=  p3 + p5            == L[4] - 1, "Side 4"
    prob +=  p4 + p0            == L[5] - 1, "Side 5"
    
def add_constraints_6p2(prob, L, p0, p1, p2, p3, p4, p5, x, y):  #DONE
    prob +=  p5 + p1 + 2*x + y  == L[0] - 3, "Side 0"
    prob +=  p0 + p2            == L[1] - 1, "Side 1"
    prob +=  p1 + p3            == L[2] - 1, "Side 2"
    prob +=  p2 + p4 + y        == L[3] - 1, "Side 3"
    prob +=  p3 + p5            == L[4] - 1, "Side 4"
    prob +=  p4 + p0            == L[5] - 1, "Side 5"
    
def add_constraints_6p3(prob, L, p0, p1, p2, p3, p4, p5, x, y): #DONE
    prob +=  p5 + p1 + 2*x + y  == L[0] - 4, "Side 0"
    prob +=  p0 + p2 + y        == L[1] - 2, "Side 1"
    prob +=  p1 + p3            == L[2] - 1, "Side 2"
    prob +=  p2 + p4            == L[3] - 1, "Side 3"
    prob +=  p3 + p5            == L[4] - 1, "Side 4"
    prob +=  p4 + p0            == L[5] - 1, "Side 5"
    
    
                
class PatchSolver6(object):
    def __init__(self, L, pattern):
        self.pattern = pattern
        self.L = L
        self.prob = LpProblem("N6 Patch", LpMaximize)

        max_p0 = float(min(L[1], L[5]) - 1)
        max_p1 = float(min(L[0], L[2]) - 1)
        max_p2 = float(min(L[1], L[3]) - 1)
        max_p3 = float(min(L[2], L[4]) - 1)
        max_p4 = float(min(L[3], L[5]) - 1)
        max_p5 = float(min(L[4], L[0]) - 1)

        p0 = LpVariable("p0",0,max_p0,LpInteger)
        p1 = LpVariable("p1",0,max_p1,LpInteger)
        p2 = LpVariable("p2",0,max_p2,LpInteger)
        p3 = LpVariable("p3",0,max_p3,LpInteger)
        p4 = LpVariable("p4",0,max_p4,LpInteger)
        p5 = LpVariable("p5",0,max_p5,LpInteger)
        
        x = LpVariable("x",0,None,LpInteger)
        
        if pattern in {2,3}:
            y = LpVariable("y",0,None,LpInteger)

        #first objective, maximize padding  
        self.prob += p0 + p1 + p2 + p3 + p4 + p5
        
        if self.pattern == 0:
            add_constraints_6p0(self.prob, L, p0, p1, p2, p3, p4, p5, x)
        elif self.pattern == 1:
            add_constraints_6p1(self.prob, L, p0, p1, p2, p3, p4, p5, x)
        elif self.pattern == 2:
            add_constraints_6p2(self.prob, L, p0, p1, p2, p3, p4, p5, x, y)
        elif self.pattern == 3:
            add_constraints_6p3(self.prob, L, p0, p1, p2, p3, p4, p5, x, y)
    
    def solve(self):
        self.prob.solve()
        
        if self.prob.status == 1:
            print(self.L)
            print('%i sided Patch with Pattern: %i' % (len(self.L),self.pattern))
            print('Status: ' + LpStatus[self.prob.status])
            for v in self.prob.variables():
                print(v.name + ' = ' + str(v.varValue))
        

class PatchSolver5():
    def __init__(self, L, pattern):
        '''
        L needs to be a list of edge subdivisions with Alpha being L[0]
        you may need to rotate or reverse L to adequately represent the patch
        '''
        self.prob = LpProblem("N5 Patch", LpMaximize)
        self.pattern = pattern
        self.L = L
        
        max_p0 = float(min(L[4] ,L[1]) - 1)
        max_p1 = float(min(L[0], L[2]) - 1)
        max_p2 = float(min(L[1], L[3]) - 1)
        max_p3 = float(min(L[2], L[4]) - 1)
        max_p4 = float(min(L[3], L[0]) - 1)

        p0 = LpVariable("p0",0,max_p0,LpInteger)
        p1 = LpVariable("p1",0,max_p1,LpInteger)
        p2 = LpVariable("p2",0,max_p2,LpInteger)
        p3 = LpVariable("p3",0,max_p3,LpInteger)
        p4 = LpVariable("p4",0,max_p4,LpInteger)
        x = LpVariable("x",0,None,LpInteger)
        y = LpVariable("y",0,None,LpInteger)

        #first objective, maximize padding  
        self.prob += p0 + p1 + p2 + p3 + p4
        
        if self.pattern == 0:
            add_constraints_5p0(self.prob, L, p0, p1, p2, p3, p4)
        elif self.pattern == 1:
            add_constraints_5p1(self.prob, L, p0, p1, p2, p3, p4, x)
        elif self.pattern == 2:
            add_constraints_5p2(self.prob, L, p0, p1, p2, p3, p4, x)
        elif self.pattern == 3:
            add_constraints_5p3(self.prob, L, p0, p1, p2, p3, p4, x, y)
            
    def solve(self):
        self.prob.solve()
        if self.prob.status == 1:
            print(self.L)
            print('%i sided Patch with Pattern: %i' % (len(self.L),self.pattern))
            print('Status: ' + LpStatus[self.prob.status])
            for v in self.prob.variables():
                print(v.name + ' = ' + str(v.varValue))
class PatchSolver4():
    def __init__(self, L, pattern):
        '''
        L needs to be a list of edge subdivisions with Alpha being L[0]
        you may need to rotate or reverse L to adequately represent the patch
        '''
        self.prob = LpProblem("N4 Patch", LpMaximize)
        self.pattern = pattern
        self.L = L
        
        max_p0 = float(min(L[3], L[1]) - 1)
        max_p1 = float(min(L[0], L[2]) - 1)
        max_p2 = float(min(L[1], L[3]) - 1)
        max_p3 = float(min(L[2], L[0]) - 1)
        p0 = LpVariable("p0",0,max_p0,LpInteger)
        p1 = LpVariable("p1",0,max_p1,LpInteger)
        p2 = LpVariable("p2",0,max_p2,LpInteger)
        p3 = LpVariable("p3",0,max_p3,LpInteger)

        if self.pattern != 0:
            x = LpVariable("x",0,None,LpInteger)
        
        if self.pattern in {2,4}:
            y = LpVariable("y",0,None,LpInteger)

        #first objective, maximize padding 
        self.prob += p0 + p1 + p2 + p3
        
        if self.pattern == 0:
            add_constraints_4p0(self.prob, L, p0, p1, p2, p3)
        elif self.pattern == 1:
            add_constraints_4p1(self.prob, L, p0, p1, p2, p3, x)
        elif self.pattern == 2:
            add_constraints_4p2(self.prob, L, p0, p1, p2, p3, x, y)
        elif self.pattern == 3:
            add_constraints_4p3(self.prob, L, p0, p1, p2, p3, x)
        elif self.pattern == 4:
            add_constraints_4p4(self.prob, L, p0, p1, p2, p3, x, y)

    def solve(self):
        self.prob.solve()
        if self.prob.status == 1:
            print(self.L)
            print('%i sided Patch with Pattern: %i' % (len(self.L),self.pattern))
            print('Status: ' + LpStatus[self.prob.status])
            for v in self.prob.variables():
                print(v.name + ' = ' + str(v.varValue))
class PatchSolver3():
    def __init__(self, L, pattern):
        '''
        L needs to be a list of edge subdivisions with Alpha being L[0]
        you may need to rotate or reverse L to adequately represent the patch
        '''
        
        self.prob = LpProblem("N6 Patch", LpMaximize)
        self.pattern = pattern
        self.L = L
        
        max_p0 = float(min(L[2], L[1]) - 1)
        max_p1 = float(min(L[0], L[2]) - 1)
        max_p2 = float(min(L[1], L[0]) - 1)

        p0 = LpVariable("p0",0,max_p0,LpInteger)
        p1 = LpVariable("p1",0,max_p1,LpInteger)
        p2 = LpVariable("p2",0,max_p2,LpInteger)
       
        if self.pattern == 1:
            x = LpVariable("x",0,None,LpInteger)

        #first objective, maximize padding
        self.prob += p0 + p1 + p2    
    
        if self.pattern == 0:
            add_constraints_3p0(self.prob, L, p0, p1, p2)
        elif self.pattern == 1:
            add_constraints_3p1(self.prob, L, p0, p1, p2, x)
    
    def solve(self):
        self.prob.solve()
        if self.prob.status == 1:
            print(self.L)
            print('%i sided Patch with Pattern: %i' % (len(self.L),self.pattern))
            print('Status: ' + LpStatus[self.prob.status])
            for v in self.prob.variables():
                print(v.name + ' = ' + str(v.varValue))
        