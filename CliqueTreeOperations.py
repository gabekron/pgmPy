import numpy as np
from CliqueTree import *
from FactorOperations import *
#import matplotlib.pyplot as plt
import networkx as nx
import pdb

def createCliqueTree( factorList,E=[]):
    """ return a Clique Tree object given a list of factors
        it peforms VE and returns the clique tree the VE
        ordering defines. See Chapter 9 of Friedman and Koller
        Probabilistic Graphical Models"""

    V=getUniqueVar(factorList)
    
    totalVars=len(V)
    cardinality=np.zeros(len(V)).tolist()
    for i in range(len(V)):
        for j in range(len(factorList)):
            try:
                indx= factorList[j].getVar().tolist().index( V[i] )
                cardinality[i]=factorList[j].getCard().tolist()[indx]
                break
            except:
                continue

    edges=np.zeros( (totalVars, totalVars))


    """ Set up adjacency matrix: for each factor, get the list of variables in its scope and create an edge between each variable in the factor """
    for f in factorList:
        variableList=f.getVar()
        for j in range(len(variableList) ):
            for k in range (len(variableList) ):
                edges[ variableList[j]-1, variableList[k]-1 ]=1

    (nrows,nedges)=np.shape(edges)            

    C=CliqueTree()
    C.setCard( cardinality )
    C.setEdges(np.zeros( (totalVars, totalVars)))
    C.setFactorList(factorList)
    C.setEvidence(E)
    C.setNodeList([])
    #print 'length of factorList: ', len(factorList)
    #print C.toString()
    cliquesConsidered = 0
    #pdb.set_trace()
    while cliquesConsidered < len(V):
        bestClique = 0
        bestScore = sys.maxint
        for i in range(nrows):
            score=np.sum( edges[i,:] )
            if score > 0 and score < bestScore:
                bestScore = score
                bestClique = i+1
        cliquesConsidered+=1
    
        (edges, factorList)=C.eliminateVar(bestClique, edges, factorList)

    return C


def PruneTree ( C ):
    """ prune a clique tree by determing if neighboring cliques are 
        supersets of each other. E.g.: [A,B,E] -- [A,B] -- [A,D] 
        pruned: [A,B,E] -- [A,D] """

    ctree_edges=C.getEdges()
    (nrows,ncols)=np.shape( ctree_edges )
    totalNodes=nrows
    Cnodes=C.getNodeList()
    
    toRemove=[]
    #print range( totalNodes )

    for i in range ( totalNodes ):
        if i in toRemove: continue
        #np.nonzero returns tuple, hence the [0]
        #we collect the neighbors of the ith clique
        neighborsI = np.nonzero ( ctree_edges[i,:] )[0].tolist()
        for c in range ( len(neighborsI) ):
            j= neighborsI[c]
            assert ( i != j), 'i cannot equal j: PruneTree'
            if j in toRemove: continue
            #here is where we look for superset neighboring nodes in the CTree
            if sum (  [ x in Cnodes[j] for x in Cnodes[i] ]  ) == len( Cnodes[i] ):
                for nk in neighborsI:
                    cnodes_i = set ( Cnodes[i] )
                    cnodes_nk= set ( Cnodes[nk] )
                    if len( list ( set.intersection( cnodes_i, cnodes_nk) ) ) == len (Cnodes[i]):
                        neighborsI_set=set( neighborsI )
                        nk_set=set( [nk] )
                        ctree_edges [ list( neighborsI_set - nk_set ), nk ] = 1
                        ctree_edges [  nk, list( neighborsI_set - nk_set )] = 1
                        break
                ctree_edges[i,:]=0
                ctree_edges[:,i]=0
                toRemove.append(i)
    toKeep =  list ( set ( range( totalNodes ) ) - set ( toRemove ) )
    for indx in toRemove:
        Cnodes[indx]=[]
    Cnodes=[ item for item in Cnodes if len(item) > 0 ]
    ctree_edges= ctree_edges[np.ix_(toKeep, toKeep)]

    C.setNodeList( Cnodes )
    C.setEdges( ctree_edges )
    #pdb.set_trace()
    #return the pruned tree with the updated nodes and edges
    return C

def CliqueTreeObserveEvidence ( C, E ):
    """ given a CliqueTree object C and list of values E, which represent evidence, update
        the factors of the cliqueTree C to reflect the observed evidence.
        Note that ObserveEvidence in FactorOperations assumes E is a Nx2 matrix,
        here we build the Nx2 matrix by assuing the jth index of E is the evidence
        for the variable j"""
    factorList= C.getFactorList()
    for j in range ( len (E)):
        if E[j] > 0:
            factorList=ObserveEvidence( factorList, np.array(np.matrix( [ j+1, E[j]] ) ) )
    C.setFactorList(factorList)
    #return the new CliqueTree object with the updated evidence
    return C


def CliqueTreeInitialPotential( C ):
    """ given a clique tree object C, calculate the initial potentials for each of the cliques
        the factors in the updated clique list are FActor objects"""

    
    N= C.getNodeCount()
    totalFactorCount=C.getFactorCount()

    nodeList=C.getNodeList()
    factorList=C.getFactorList()

    cliqueList=[ Factor( [], [], [], str(i) )  for i in range(N)  ]
    #edges=np.zeros( (N,N) )

    """ First assign the factors to appropriate cliques
    based on the skeleton cliqueTree cTree"""

    factorsUsed=np.zeros( totalFactorCount, dtype=int).tolist()
    #pdb.set_trace()
    for i in range(N):
        cliqueList[i].setVar( nodeList[i] )
        F=[]
        """ we add factors to the clique if they are in the variable scope of the clique """
        for j in range( len(factorList) ):
            if len( factorList[j].getVar().tolist() ) == len ( list( set.intersection ( set(cliqueList[i].getVar().tolist() ), set( factorList[j].getVar().tolist() ) ) ) ):
        
                if factorsUsed[j] == 0:
                    F.append( factorList[j] )
                    factorsUsed[j] = 1
    #print F
        #pdb.set_trace()
        #F= [ f.getFactor() for f in F ]
        cliqueList[i]=ComputeJointDistribution ( F )
        #pdb.set_trace()
    C.setNodeList(cliqueList)
    #pdb.set_trace()
    return C

def getNextClique(P, messages):

    """ we need to come up wih a proper message passing order. A clique is ready to pass
        messages upward once its recieved all downstream messages from its neighbor (and vice versa)
        its ready to transmit downstream once it recieves all its upstream messages

        the ith clique C_i is ready to transmit to its neighbor C_j when C_i recieves all its
        messages from neigbors except C_j. In cTree message passing, each message is passed
        once.  To get the process started we start with our initial potential cTree, P
        and an empty matrix of factors, representing messages passed between the nodes on the clique
        tree """
    i=j=-1
    edges=P.getEdges()
    #print edges
    (nrow, ncol) = np.shape(edges)

    for r in range(nrow):
        
        #we want to ignore nodes with only one neighbor
        #becuae they are ready to pass messages
        if np.sum(edges[r,:] ) == 1:
            continue 

        foundmatch=0

        for c in range(ncol):
            if  edges[r,c] == 1 and messages[r,c].getVarCount()  == 0:
                #list of indices indicating neighbors or r
                #print 'r,c: ', r, ' ', c
                #print 'edges[r,c]: ', edges[r,c]
                Nbs=np.nonzero(edges[:,r])[0]
                #print 'Nbs before:', Nbs
                Nbs=Nbs[np.nonzero(Nbs!= c)[0]]
                #print 'Nbs after: ', Nbs
                allnbmp=1 #neighbors messages passed?
                
                #find all of r's neighbors have sent messages *to* r
                for z in range( len(Nbs) ):
                    #print messages[Nbs[z],r].getVarCount()
                    if messages[ Nbs[z],r].getVarCount()  == 0:
                        allnbmp=0

                if allnbmp == 1:
                    foundmatch=1
                    break
        
        if foundmatch==1:
            #sys.stderr.write("found match!\n")
            i=r
            j=c
            break
       
    return (i,j)


def CliqueTreeCalibrate( P, isMax=False):
    """ this function performs sum-product or max-product algorithm for clique tree calibration.
        P is the CliqueTree object. isMax is a boolean flag that when set to True performs Max-Product
        instead of the default Sum-Product. The function returns a calibrated clique tree in which the
        values of the factors is set to final calibrated potentials.

        Once a tree is calibrated, in each clique (node) contains the marginal probability over the variables in
        its scope. We can compute the marginal probability of a variable X by choosing a clique that contains the
        variable of interest, and summing out non-query variables in the clique. See page 357 in Koller and Friedman

        B_i(C_i)= sum_{X-C_i} P_phi(X)

        The main advantage of clique tree calibration is that it facilitates the computation of posterior
        probabliity of all variables in the graphical model with an efficient number of steps. See pg 358
        of Koller and Friedman

        After calibration, each clique will contain the marginal (or max-mariginal, if isMax is set to True)

        """
    
    np.set_printoptions(suppress=True)
    ctree_edges=P.getEdges()

    ctree_cliqueList=P.getNodeList()

    """ if max-sum, we work in log space """
    if isMax == True:
        ctree_cliqueList= [ LogFactor (factor) for factor in ctree_cliqueList ]

    
    
    N=P.getNodeCount() #Ni is the total number of nodes (cliques) in cTree

    #dummyFactor=Factor( [], [], [], 'factor')
    #set up messsages to be passed
    #MESSAGES[i,j] represents the message going from clique i to clique j
    #MESSAGES will be a matrix of Factor objects
    MESSAGES=np.tile( Factor( [], [], [], 'factor'), (N,N))
    DUMMY=np.reshape( np.arange(N*N)+1, (N,N) )
    

    """While there are ready cliques to pass messages between, keep passing
    messages. Use GetNextCliques to find cliques to pass messages between.
    Once you have clique i that is ready to send message to clique
    j, compute the message and put it in MESSAGES(i,j).
    Remember that you only need an upward pass and a downward pass."""

    """ leaf nodes are ready to pass messages right away
        so we initialize MESSAGES with leaf message factors
        recall, a node is a leave if row sum is equal to 1"""
    for row in range(N):
        rowsum= np.sum( ctree_edges[row,:] )
        if rowsum ==1 :
            #Returns a tuple of arrays, one for each dimension, we want the first, hence the [0]
            leafnode=np.nonzero( ctree_edges[row,:] )[0].tolist()[0]
            #I discovered NumPy set operations http://docs.scipy.org/doc/numpy/reference/routines.set.html
            marginalize=np.setdiff1d( ctree_cliqueList[row].getVar(),  ctree_cliqueList[leafnode].getVar() ).tolist()
            sepset=np.intersect1d( ctree_cliqueList[row].getVar(), ctree_cliqueList[leafnode].getVar() ).tolist()

            """ if isMax is false, this is sumproduct, so we do factor marginalization """
            if isMax == 0:
                #MESSAGES(row,leafnode)=FactorMarginalization(P.cliqueList(row),marginalize);
                MESSAGES[row,leafnode]=FactorMarginalization(ctree_cliqueList[row], marginalize )
                if np.sum( MESSAGES[row,leafnode].getVal() ) != 1:
                    newVal=MESSAGES[row,leafnode].getVal() / np.sum( MESSAGES[row,leafnode].getVal() )
                    MESSAGES[row,leafnode].setVal(newVal)
            else:
                """ if isMax is true, this is max-marginalization
                    don't normalize the value just yet"""
                MESSAGES[row,leafnode]=FactorMaxMarginalization( ctree_cliqueList[row], marginalize  )


    
    """ now that the leaf messages are initialized, we begin with the rest of the clique tree
    now we do a single pass to arrive at the calibrated clique tree. We depend on
    GetNextCliques to figure out which nodes i,j pass messages to each other"""
    
    while True:
        (i,j)=getNextClique(P,MESSAGES)
        if sum ( [ i, j] ) == -2:
            break
        #print 'i: ', i, 'j: ', j
        """ similiar to above, we figure out the sepset and what variables to marginalize out
        between the two cliques"""
        marginalize=np.setdiff1d( ctree_cliqueList[i].getVar(),  ctree_cliqueList[j].getVar() ).tolist()
        sepset=np.intersect1d( ctree_cliqueList[i].getVar(), ctree_cliqueList[j].getVar() ).tolist()

        """ find all the incoming neighbors, except j """
        Nbs=np.nonzero( ctree_edges[:,i])[0] #returns a tuple ...
        Nbs_minusj=[ elem for elem in Nbs if elem !=  j ]
        #print 'Nbs_minusj: ', Nbs_minusj, ' [i]: ', [i]
        #see numpy for matlab users http://www.scipy.org/NumPy_for_Matlab_Users
        # these are incoming messages to the ith clique
        Nbsfactors=MESSAGES[np.ix_(Nbs_minusj, [i] )].flatten().tolist()
        #print DUMMY[np.ix_(Nbs_minusj, [i] )].flatten()
        #for f in Nbsfactors:
            #print f
        """ this is sum/product """
        if isMax == 0:
            #print 'total number of Nbs factors: ', len(Nbsfactors)
            if len(Nbsfactors) == 1:
                Nbsproduct=FactorProduct( Nbsfactors[0], IdentityFactor(Nbsfactors[0]) )
            else:
                Nbsproduct=ComputeJointDistribution( Nbsfactors )
            #pdb.set_trace()
            #val=Nbsproduct.getVal()
            #rowcount=len(val)/3
            #print Nbsproduct.getVar()
            #print Nbsproduct.getCard()
            #print np.reshape( val, (rowcount,3))
            #now mulitply wiht the clique factor
            
            CliqueNbsproduct=FactorProduct( Nbsproduct, ctree_cliqueList[i] )
            
            CliqueMarginal= FactorMarginalization ( CliqueNbsproduct, marginalize )
            
            #normalize the marginal
            newVal=CliqueMarginal.getVal() / np.sum( CliqueMarginal.getVal() )

            CliqueMarginal.setVal( newVal )
            
            MESSAGES[i,j] = CliqueMarginal
        else:
            if len(Nbsfactors) == 1:
                Nbssum=Nbsfactors[0]
            else:
                Nbssum=reduce ( lambda x,y: FactorSum(x,y), Nbsfactors  )
            CliqueNbsSum=FactorSum( Nbssum, ctree_cliqueList[i] )
            CliqueMarginal=FactorMaxMarginalization( CliqueNbsSum, marginalize )
            MESSAGES[i,j] = CliqueMarginal
        #print



    #######################################################################
    """ once out the while True loop, the clique tree has been calibrated
    here is where we compute final belifs (potentials) for the cliques and place them in """

    for i in range ( len(ctree_cliqueList)):
        Nbs=np.nonzero( ctree_edges[:,i])[0]#returns a tuple
        Nbsfactors=MESSAGES[np.ix_(Nbs, [i])].flatten().tolist()

        if isMax == 0:
            if len(Nbsfactors) == 1:
                Nbsproduct=FactorProduct( Nbsfactors[0], IdentityFactor(Nbsfactors[0]) )
            else:
                Nbsproduct=ComputeJointDistribution ( Nbsfactors)
            
            CliqueNbsProduct=FactorProduct(Nbsproduct, ctree_cliqueList[i])
            #pdb.set_trace()
            ctree_cliqueList[i]=CliqueNbsProduct
        else:
            if len(Nbsfactors) == 1:
                Nbssum=Nbsfactors[0]
            else:
                Nbssum=reduce ( lambda x,y: FactorSum(x,y), Nbsfactors  )
            CliqueNbsSum=FactorSum(Nbssum, ctree_cliqueList[i])
            ctree_cliqueList[i]=CliqueNbsSum
    
    P.setNodeList( ctree_cliqueList )
    #np.savetxt( 'numpy.cTree.edges.calibrated.txt',ctree_edges,fmt='%d', delimiter='\t')
    
    #pdb.set_trace()
    #return P
    return (P, MESSAGES)
    #for k in range(len(ctree_cliqueList)):
    #    print 'k: ', k
    #    print ctree_cliqueList[k]
        #IndexToAssignment(1:prod(P.cliqueList(1).card), P.cliqueList(1).card)
    #    I=np.arange(np.prod( ctree_cliqueList[k].getCard()  ))
    #    print IndexToAssignment( I, ctree_cliqueList[k].getCard()  )
    #    print "=="

    #return P


def CreatePrunedInitCtree(F,E=[]):
    """ 1. create cTree from list of factors F and evidence E
        2. prune it
        3. compute initial potential of the tree
        4. return it"""

    cTree = createCliqueTree(F,E)
    prunedCTree=PruneTree( cTree )
    prunedCTree.incorporateEvidence()
    return CliqueTreeInitialPotential( prunedCTree )

    

def ComputeExactMarginalsBP( F, E=[], isMax=False, computeJoint=0):
    """ We take a list of Factor objects, observed Evidence E
        and returns marignal proabilities for the variables in the
        Bayesian network. If isMax is 1 it runs MAP inference ( *still need to
        do this *) otherwise it runs exact inference using Sum/Product algorithm.
        The ith element of the returned list represents the ith variable in the
        network and its marginal prob of the variable

        Note, we implicitly create, prune, initialize, and calibrate a clique tree
        constructed from the factor list F  """

    MARGINALS=[]
    #pdb.set_trace()
    P = CreatePrunedInitCtree(F,E)
    #G=nx.from_numpy_matrix( P.getEdges() )
    #nx.draw_shell(G)
    #plt.show()
    
    #plt.savefig('cliqueTree.png', bbox_inches=0)
    (P,MESSAGES) = CliqueTreeCalibrate(P,isMax)
    #pdb.set_trace()
    if computeJoint==1:
        jointDistribution=ComputeJointDistributionFromCalibratedCliqueTree(P, MESSAGES, isMax)
    else:
        jointDistribution=None
    #pdb.set_trace()
    #P = CliqueTreeCalibrate(P,isMax)
    cliqueList=P.getNodeList()
    
    fh=open('ExactMarginals.CliqueTree.log','a')
    for i in range(len(cliqueList)):
        out = ",".join( map(str, cliqueList[i].getVar().tolist() )) 
        outstring= "node " + str(i) + ":\t" + out +'\n'
        fh.write(outstring)
    fh.write("\n")
    #np.savetxt( 'numpy.cTree.edges.calibrated.txt',P.getEdges(),fmt='%d', delimiter='\t')
    np.savetxt('ExactMarginals.CliqueTree.log',P.getEdges(),fmt='%d', delimiter='\t')
    
    
                           
                            
    """ get the list of unique variables """
    V=getUniqueVar(F)
    

    for i in range ( len(V ) ):
        for j in range ( len(cliqueList ) ):
            if V[i] in cliqueList[j].getVar():
                marginalize=np.setdiff1d ( cliqueList[j].getVar(), V[i]  ).tolist()
                if not marginalize:
                    MARGINALS.append( cliqueList[j]  )
                else:
                    if isMax == 0:
                        #mfactor=FactorMarginalization(P.cliqueList(j), marginalize);
                        mfactor=FactorMarginalization( cliqueList[j], marginalize )
                        newVal=mfactor.getVal() / np.sum( mfactor.getVal() )
                        mfactor.setVal( newVal )
                        MARGINALS.append ( mfactor )
                    else:
                        mfactor=FactorMaxMarginalization( cliqueList[j], marginalize )
                        MARGINALS.append( mfactor )
                break

    
    return (MARGINALS,jointDistribution)

def ComputeJointDistributionFromCalibratedCliqueTree( P, MESSAGES, isMax=0):
    
    """ this is a function to attempt to compute the joint distribution from
        a calibrated clique tree (cTree). The arguments are: 
        1. The calibrated cTree, P, which is a CliqueTree object
        2. The sepset beliefs are is the matrix MESSAGES
           The MESSAGES matrix is a matrix of Factor objects
           We can get the indices of the sepset messages
           from the edges of the clique tree. 
        
        This function attempts to implement equation 10.10 in Koller and Friedman
        in section 10.2.3: A Calibrated Clique Tree as a Distribution
        
        P_\Phi(X) = \frac{ \prod_{i \in V_T} \Beta_i(C_i)   } { \prod_{i-j} \in E_T \mu_i,j(S_i,j)   }
        
        Basically A) multiply the clique beliefs 
                  B) multiply the sepset beliefs
                  C) divide A/B 
        
        
         """
    cliqueFactors=P.getNodeList()
   
    """ if this is a max-marginal calibrated clique tree the values are in log space
        Just re-exponentiate them  """
    if isMax==1:
        cliqueFactors = [ ExpFactorNormalize(c) for c in cliqueFactors ]
    
    """ this is the numerator """
    cliqueBeliefProducts=reduce(lambda x, y: FactorProduct(x,y), cliqueFactors)
    
    """ get the adjacency matrix of the clique tree """
    adj_matrix=P.getEdges()
    
    """ get the nonzero indices, then compute the product of the sepset beliefs """
    nonzero_rows=adj_matrix.nonzero()[0].tolist()
    nonzero_cols=adj_matrix.nonzero()[1].tolist()
    
    

    
    
    sepsetBeliefsFactors= [   MESSAGES[x,y] for (x,y) in zip(nonzero_rows, nonzero_cols) ] 
    
    """ if this is a max-marginal calibrated clique tree the values are in log space
        Just re-exponentiate them  """
    if isMax == 1:
        sepsetBeliefsFactors = [ ExpFactorNormalize(c) for c in sepsetBeliefsFactors ]
    
    
    
    sepsetBeliefProducts= reduce( lambda x,y: FactorProduct(x,y), sepsetBeliefsFactors)
         
    """ the re-parameterization of the joint (clique tree invariant)  
        divide the clique beliefs by the sepset messages  """
    jointDistrbution=FactorDiv(cliqueBeliefProducts, sepsetBeliefProducts)
    
    val=jointDistrbution.getVal()/np.sum( jointDistrbution.getVal() )
    jointDistrbution.setVal( val )
    
    return jointDistrbution
    
         
         
         
         
         
         
        
