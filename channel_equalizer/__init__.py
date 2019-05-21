# channel_equalizer class 
# Last modification by Marko Kosunen, marko.kosunen@aalto.fi, 05.01.2018 11:07
#Add TheSDK to path. Importing it first adds the rest of the modules
#Simple buffer template
import os

import numpy as np
#import tempfile

from thesdk import *
from verilog import *
from verilog.testbench import *
from verilog.testbench import testbench as vtb
from signal_generator_802_11n import PLPCsyn_long


class channel_equalizer(verilog,thesdk):
    @property
    def _classfile(self):
        return os.path.dirname(os.path.realpath(__file__)) + "/"+__name__

    def __init__(self,*arg): 
        self.proplist = [ 'Rs', 'symbol_length', 'Users' ];    #properties that can be propagated from parent
        self.Rs = 160e6;                   # Sampling frequency
        self.Users = 16;                   # Number of users
        self.symbol_length  = 64;          # OFDM symbol length
        self.A = IO();            # Input data, FFT Bins in series 
        self.estimate_sync = IO();            
        self.equalize_sync = IO();            
        self.estimate_user_index= IO();            
        self._Z = IO();           # Output, equalized FFT bins
        self.control_write = IO()
        self.control_write.Data = Bundle()
        self._control_read = IO()
        self.model='py';             #can be set externally, but is not propagated
        self.par= False              #By default, no parallel processing
        self.queue= []               #By default, no parallel processing

        if len(arg)>=1:
            parent=arg[0]
            self.copy_propval(parent,self.proplist)
            self.parent =parent;
        self.init()
    def init(self):
        #This gets updated every time you add an iofile
        #self.iofile_bundle=Bundle()
        #Adds files to bundle
        _=verilog_iofile(self,name='Z',datatype='complex')
        _=verilog_iofile(self,name='control_read',datatype='complex')
        _=verilog_iofile(self,name='A',dir='in')
        _=verilog_iofile(self,name='estimate_sync',dir='in')
        _=verilog_iofile(self,name='equalize_sync',dir='in')
        _=verilog_iofile(self,name='estimate_user_index',dir='in')
        self.vlogparameters=dict([ ('g_Rs',self.Rs),])

    def main(self):
        out=np.array(self.A.Data)
        if self.par:
            self.queue.put(out)
        self._Z.Data=out

    def run(self,*arg):
        if len(arg)>0:
            self.par=True      #flag for parallel processing
            self.queue=arg[0]  #multiprocessing.queue as the first argument
        if self.model=='py':
            self.main()
        else: 
          if self.model=='sv':
              self.control_write.Data.Members['control_write'].adopt(parent=self)

              # Create testbench and execute the simulation
              self.define_testbench()
              self.tb.export(force=True)
              self.write_infile()
              self.run_verilog()
              self.read_outfile()
              del self.iofile_bundle

          elif self.model=='vhdl':
              self.print_log(type='F', msg='VHDL model not yet supported')

    def write_infile(self):
        #Input file data definitions
        self.iofile_bundle.Members['A'].data=self.A.Data
        self.iofile_bundle.Members['estimate_sync'].data=self.estimate_sync.Data
        self.iofile_bundle.Members['estimate_user_index'].data=self.estimate_user_index.Data
        self.iofile_bundle.Members['equalize_sync'].data=self.equalize_sync.Data

        # This could be a method somewhere
        for name, val in self.iofile_bundle.Members.items():
            if val.dir=='in':
                self.iofile_bundle.Members[name].write()

    def read_outfile(self):
        #Handle the ofiles here as you see the best
        self.iofile_bundle.Members['Z'].read()
        self.iofile_bundle.Members['control_read'].read()
        self._Z.Data=self.iofile_bundle.Members['Z'].data
        self._control_read.Data=self.iofile_bundle.Members['control_read'].data

        if self.par:
            self.queue.put(self._Z)
            self.queue.put(self._control_read)



    # Testbench definition method
    def define_testbench(self):
        #Initialize testbench
        self.tb=vtb(self)
        # Create TB connectors from the control file
        for connector in self.control_write.Data.Members['control_write'].verilog_connectors:
            self.tb.connectors.Members[connector.name]=connector
            # Connect them to DUT
            try: 
                self.dut.ios.Members[connector.name].connect=connector
            except:
                pass

        # Dut is created automaticaly, if verilog file for it exists
        self.tb.connectors.update(bundle=self.tb.dut_instance.io_signals.Members)

        #Assign verilog simulation parameters to testbench
        self.tb.parameters=self.vlogparameters

        # Copy iofile simulation parameters to testbench
        for name, val in self.iofile_bundle.Members.items():
            self.tb.parameters.Members.update(val.vlogparam)

        # Define the iofiles of the testbench. '
        # Needed for creating file io routines 
        self.tb.iofiles=self.iofile_bundle

        #Define testbench verilog file
        self.tb.file=self.vlogtbsrc


        ## Start initializations
        #Init the signals connected to the dut input to zero
        for name, val in self.tb.dut_instance.ios.Members.items():
            if val.cls=='input':
                val.connect.init='\'b0'

        # IO file connector definitions
        # Define what signals and in which order and format are read form the files
        # i.e. verilog_connectors of the file
        # All connectors should be already defined at this phase
        name='control_write'
        ionames=[ _.name for _ in self.control_write.Data.Members[name].verilog_connectors ]
        self.iofile_bundle.Members[name].verilog_connectors=\
                self.tb.connectors.list(names=ionames)
        
        #for name in ionames:
        #    self.tb.connectors.Members[name].type='signed'

        name='estimate_sync'
        ionames=[]
        ionames+=['io_estimate_sync']
        self.iofile_bundle.Members[name].verilog_connectors=\
                self.tb.connectors.list(names=ionames)
        self.iofile_bundle.Members[name].verilog_io_condition='initdone'

        name='estimate_user_index'
        ionames=[]
        ionames+=['io_estimate_user_index']
        self.iofile_bundle.Members[name].verilog_connectors=\
                self.tb.connectors.list(names=ionames)
        self.iofile_bundle.Members[name].verilog_io_condition='initdone'

        name='equalize_sync'
        ionames=[]
        ionames+=['io_equalize_sync']
        self.iofile_bundle.Members[name].verilog_connectors=\
                self.tb.connectors.list(names=ionames)
        self.iofile_bundle.Members[name].verilog_io_condition='initdone'

        name='A'
        ionames=[]
        ionames+=['io_A_real', 'io_A_imag' ]
        self.iofile_bundle.Members[name].verilog_connectors=\
                self.tb.connectors.list(names=ionames)
        self.iofile_bundle.Members[name].verilog_io_condition='initdone'

        name='Z'
        ionames=[]
        for user in range(self.Users):
           ionames+= [ 'io_Z_%s_real' %(user) , 
                     'io_Z_%s_imag' %(user)] 
        self.iofile_bundle.Members[name].verilog_connectors=\
                self.tb.connectors.list(names=ionames)

        self.iofile_bundle.Members[name].verilog_io_condition_append(cond='&& initdone')
        for name in ionames:
            self.tb.connectors.Members[name].type='signed'

        name='control_read'
        ionames=[]
        for user in range(self.Users):
           ionames+= [ 'io_estimate_out_%s_real' %(user) , 
                     'io_estimate_out_%s_imag' %(user)] 
        self.iofile_bundle.Members[name].verilog_connectors=\
                self.tb.connectors.list(names=ionames)

        self.iofile_bundle.Members[name].verilog_io_condition_append(cond='&& initdone')
        # Should be ok, we just need somthing that trigs the writing to file
        # and is proportional to scan
        self.iofile_bundle.Members[name].verilog_io_sync='@(negedge io_estimate_read_en)\n'
        for name in ionames:
            self.tb.connectors.Members[name].type='signed'

        ## This method is in verilog_testbench class
        self.tb.generate_contents()



if __name__=="__main__":
    import matplotlib.pyplot as plt
    from  channel_equalizer import *
    from  channel_equalizer.controller import controller as channel_equalizer_controller
    from signal_generator_802_11n import PLPCsyn_long
    import pdb
    
    chlen=64
    len=16*chlen
    phres=64
    fsig=25e6
    refmaxval=30000
    #mode=0  ## Invert channel on chip
    mode=1  ## Invert channel externally
    #indata=2**10*np.exp(1j*2*np.pi/phres*(np.arange(len)*np.round(fsig/dut.Rs*phres)))\
    #        .reshape(-1,1)
    #indata=np.arange(1,2**13).astype(complex).reshape(-1,1)*(1+1j)
    #indata=np.ones((1,2**13)).astype(complex).reshape(-1,1)*(1+1j)
    onerows=np.ones((int(2**13/chlen),1),dtype=complex)
    tdata=np.round((onerows*PLPCsyn_long.T)*1024)
    #channel=onerows*np.ones((1,chlen))+1j*np.ones((1,chlen))
    channel=onerows*((np.arange(chlen)/chlen+1j*np.arange(chlen)/chlen).reshape(1,-1))
    #Should cap the max value to 1
    #channel=onerows*((np.random.normal(0,0.01,chlen)+1j*np.random.normal(0,0.1,chlen)).reshape(1,-1))

    #indata[0,0]=1+1j*1 # To help syncing
    indata=np.round(tdata * channel).reshape(-1,1)
    #indata[0:64:,0]=1+1j #Sync help
    equalize_sync=np.zeros((indata.shape[0],1))
    estimate_sync=np.zeros((indata.shape[0],1))

    controller=channel_equalizer_controller()
    controller.reset()
    controller.reset_estimate_memories()
    controller.step_time(step=10*controller.step)
    controller.write_reference_sequence(maxval=refmaxval)
    controller.set_estimate_format(value=mode)
    controller.step_time()

    equalize_sync[0::128]=1
    controller.start_datafeed()
    controller.step_time(step=125*controller.step)
    estimate_sync[0:16*128:128,0]=1
    estimate_user_index=(np.cumsum(estimate_sync)-1).reshape(-1,1)
    controller.step_time(step=16*128*controller.step)
    controller.set_estimate_zeros()
    controller.read_estimate_out()

    dut=channel_equalizer()
    dut2=channel_equalizer()
    dut.model='py'
    dut2.model='sv'
    for d in [ dut, dut2 ]: 
        d.interactive_verilog=False
        d.A.Data=indata
        d.estimate_sync.Data=estimate_sync
        d.estimate_user_index.Data=estimate_user_index
        d.equalize_sync.Data=equalize_sync
        d.control_write=controller.control_write
        d.A.Data=indata
        d.estimate_sync.Data=estimate_sync
        d.estimate_user_index.Data=estimate_user_index
        d.equalize_sync.Data=equalize_sync
        d.control_write=controller.control_write
        d.run()
    #Compute the estimates
    addresses=[0,1,2,3,4,5,32,59,60,61,62,63]
    #estimated_data=dut2._control_read.Data[0:64,0].reshape(-1,1)*np.ones((1,16))
    estimated_data=dut2._control_read.Data
    zf_matrix=np.array([],dtype='complex')
    for bin in range(64):
        c=(dut2._control_read.Data[bin,:]/2**16).reshape(-1,1) ##Channel estimate
        bf=((1/c).T*(2**16-1)).real.astype(int)+1j*((1/c).T*(2**16-1)).imag.astype(int)
        bftest=c*bf
        zf=(np.linalg.pinv(np.conj(c)*c.T)*np.conj(c)).T*2**16
        if bin==0:
            bf_matrix=bf.reshape(1,-1)
            zf_matrix=((zf.real).astype(int)+1j+zf.imag.astype(int)).reshape(1,-1)
        else:
            bf_matrix=np.r_['0', bf_matrix, bf.reshape(1,-1) ]
            zf_matrix=np.r_['0', zf_matrix, zf.reshape(1,-1) ]
    
    bf_matrix[addresses,:]=0+1j*0
    zf_matrix[addresses,:]=0+1j*0

    #restart simulation
    estimate_sync=np.zeros((indata.shape[0],1))
    controller.reset_control_sequence()
    controller.reset()
    controller.set_estimate_format(value=mode)
    controller.write_reference_sequence(maxval=refmaxval)
    if mode==0:
        controller.write_estimate_sequence(data=estimated_data)
    elif mode==1:
        controller.write_estimate_sequence(data=bf_matrix)
    controller.step_time()
    controller.start_datafeed()
    controller.step_time(step=2**10*controller.step)
    controller.read_estimate_out()
    for d in [ dut, dut2 ]: 
        d.interactive_verilog=False
        d.estimate_sync.Data=estimate_sync
        d.run()

    f0=plt.figure(0)
    x_ref=np.arange(64).reshape(-1,1) 
    seq_ref=controller.reference_sequence.reshape(-1,1)
    startindex=5750  #This is a random number within the valid output range
    offset=np.argmax(np.abs(np.correlate(
        dut2._Z.Data[startindex:startindex+127,0].reshape(-1),
        controller.reference_sequence.reshape(-1))))
    #print(offset) 
    ##pdb.set_trace()
    seq_equalized=dut2._Z.Data[startindex+offset:startindex+offset+64,0].reshape(-1,1)
    plt.plot(x_ref,seq_ref.real,x_ref,seq_equalized.real)
    plt.xlim(0,63)
    plt.suptitle("Verilog model")
    plt.xlabel("Bin")
    plt.ylabel("Symbol")
    plt.grid()
    plt.show(block=False)
    f0.savefig('sequences_verilog.eps', format='eps', dpi=300);

    print(seq_equalized.shape)
    print(seq_ref.shape)
    err=(seq_ref-seq_equalized)
    print(err.shape)

    f1=plt.figure(1)
    plt.plot(x_ref,err)
    plt.xlim(0,63)
    plt.suptitle("Verilog model")
    plt.xlabel("Bin")
    plt.ylabel("Symbol error")
    plt.grid()
    plt.show(block=False)
    f1.savefig('sequences_diff.eps', format='eps', dpi=300);
    input()

