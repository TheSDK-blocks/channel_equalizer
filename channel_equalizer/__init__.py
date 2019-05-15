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
        self._Z = IO();           # Output, equalized FFT bins
        self.control_write = IO()
        self.control_write.Data = Bundle()
        self.control_out = IO()
        self.control_out.Data = Bundle()
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
        self.iofile_bundle=Bundle()
        #Adds files to bundle
        _=verilog_iofile(self,name='Z',datatype='complex')
        _=verilog_iofile(self,name='A',dir='in')
        _=verilog_iofile(self,name='estimate_sync',dir='in')
        _=verilog_iofile(self,name='equalize_sync',dir='in')
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
              self.control_write.Data.Members['control_file'].adopt(parent=self)

              # Create testbench and execute the simulation
              self.define_testbench()
              self.tb.export(force=True)
              self.write_infile()
              self.run_verilog()
              #self.read_outfile()
              #del self.iofile_bundle

          elif self.model=='vhdl':
              self.print_log(type='F', msg='VHDL model not yet supported')

    def write_infile(self):
        #Input file data definitions
        self.iofile_bundle.Members['A'].data=self.A.Data
        self.iofile_bundle.Members['estimate_sync'].data=self.estimate_sync.Data
        self.iofile_bundle.Members['equalize_sync'].data=self.equalize_sync.Data

        # This could be a method somewhere
        for name, val in self.iofile_bundle.Members.items():
            if val.dir=='in':
                self.iofile_bundle.Members[name].write()

    def read_outfile(self):
        #Handle the ofiles here as you see the best
        a=self.iofile_bundle.Members['Z']
        a.read(dtype='object')
        self._Z.Data=a.data
        print(self._Z.Data)
        if self.par:
            self.queue.put(self._Z)



    # Testbench definition method
    def define_testbench(self):
        #Initialize testbench
        self.tb=vtb(self)

        # Create TB connectors from the control file
        for connector in self.control_write.Data.Members['control_file'].verilog_connectors:
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
        name='control_file'

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
        for user in range(1):
           ionames+= [ 'io_Z_%s_real' %(user) , 
                     'io_Z_%s_imag' %(user)] 
        self.iofile_bundle.Members[name].verilog_connectors=\
                self.tb.connectors.list(names=ionames)

        self.iofile_bundle.Members[name].verilog_io_condition_append(cond='&& initdone')
        for name in ionames:
            self.tb.connectors.Members[name].type='signed'

        ## This method is in verilog_testbench class
        self.tb.generate_contents()



if __name__=="__main__":
    import matplotlib.pyplot as plt
    from  channel_equalizer import *
    from  channel_equalizer.controller import controller as channel_equalizer_controller
    from signal_generator_802_11n import PLPCsyn_long
    chlen=64
    len=16*chlen
    phres=64
    fsig=25e6
    #indata=2**10*np.exp(1j*2*np.pi/phres*(np.arange(len)*np.round(fsig/dut.Rs*phres)))\
    #        .reshape(-1,1)
    #indata=np.arange(1,2**13).astype(complex).reshape(-1,1)*(1+1j)
    #indata=np.ones((1,2**13)).astype(complex).reshape(-1,1)*(1+1j)
    tdata=np.round((np.ones((int(2**13/64),1),dtype=complex)*PLPCsyn_long.T).reshape(-1,1)*1024)
    channel=(np.ones((int(2**13/64),1))*(np.random.normal(0,1,chlen)+1j*np.random.normal(0,1,chlen)).reshape(1,-1)).reshape(-1,1)
    print(tdata.shape)
    print(channel.shape)
    #indata[0,0]=1+1j*1 # To help syncing
    indata=np.round((tdata[:,0] * channel[:,0])).reshape(-1,1)
    indata[0:64:,0]=1+1j #Sync help
    equalize_sync=np.zeros((indata.shape[0],1))
    estimate_sync=np.zeros((indata.shape[0],1))

    controller=channel_equalizer_controller()
    controller.reset()
    controller.write_reference_sequence()
    controller.set_estimate_format(value=1)
    controller.step_time()

    estimate_sync[0,0]=1
    equalize_sync[0::128]=1
    controller.start_datafeed()
    controller.step_time(step=125*controller.step)
    controller.set_estimate_format(value=0)
    estimate_sync[128,0]=1
    controller.step_time(step=100*controller.step)
    controller.set_estimate_zeros()
    dut=channel_equalizer()
    dut2=channel_equalizer()
    dut.model='py'
    dut2.model='sv'
    dut2.interactive_verilog=True
    dut.A.Data=indata
    dut.estimate_sync.Data=estimate_sync
    dut.equalize_sync.Data=equalize_sync
    dut.control_write=controller.control_write
    dut2.A.Data=indata
    dut2.estimate_sync.Data=estimate_sync
    dut2.equalize_sync.Data=equalize_sync
    dut2.control_write=controller.control_write

    dut.run()
    dut2.run()
    #f0=plt.figure(0)
    #plt.plot(np.abs(dut._io_out.Data[10,:]))
    #plt.suptitle("Python model")
    #plt.xlabel("Freq")
    #plt.ylabel("Abs(FFT)")
    #plt.show(block=False)
    #f0.savefig('fft_python.eps', format='eps', dpi=300);
    #f1=plt.figure(1)
    #plt.plot(np.abs(dut2._io_out.Data[10,:]))
    #plt.suptitle("Verilog model")
    #plt.xlabel("Freq")
    #plt.ylabel("Abs(FFT)")
    #plt.show(block=False)
    #f1.savefig('fft_verilog.eps', format='eps', dpi=300);
    #input()

