# Written by Marko kosunen, Marko.kosunen@aalto.fi 20190509
# The right way to do the unit controls is to write a controller class here
import os

import numpy as np
from thesdk import *
from verilog import *
from verilog.module import *

from signal_generator_802_11n import PLPCsyn_long

class controller(verilog,thesdk):
    @property
    def _classfile(self):
        return os.path.dirname(os.path.realpath(__file__)) + "/"+__name__

    def __init__(self,*arg): 
        self.proplist = [ 'Rs', 'symbol_length', 'Users' ];    #properties that can be propagated from parent
        self.Rs = 160e6;                   # Sampling frequency
        self.step=int(1/(self.Rs*1e-12))   #Time increment for control
        self.Users = 16;                   # Number of users
        self.symbol_length  = 64;          # OFDM symbol length
        self.time=0
        self.A = IO();            # Input data, FFT Bins in series 
        self._Z = IO();           # Output, equalized FFT bins
        self.control_write = IO()
        self.control_write.Data = Bundle()
        self.control_read = IO()
        self.control_read.Data = Bundle()
        self.model='py';             #can be set externally, but is not propagated
        self.par= False              #By default, no parallel processing
        self.queue= []               #By default, no parallel processing

        if len(arg)>=1:
            parent=arg[0]
            self.copy_propval(parent,self.proplist)
            self.parent =parent;


        # We now where the verilog file is. 
        # Let's read in the file to have IOs defined
        self.dut=verilog_module(file=self.entitypath + 
                '/../channel_equalizer/sv/channel_equalizer.sv')

        # Scan is the way to pass the controls# 
        # Format: Time in rows, 
        # Signals in columns, first column is the timestamp
        self._scan = IO();           # Pointer for output data
        self._scan.Data=Bundle()

        # Define the signal connectors associeted with this 
        # controller
        # These are signals of tb driving several targets
        # Not present in DUT
        self.connectors=verilog_connector_bundle()

        if len(arg)>=1:
            parent=arg[0]
            self.copy_propval(parent,self.proplist)
            self.parent =parent;

        #These are signals not in dut
        self.newsigs_write=[
                 'initdone',
                ]

        # Selected signals controlled with this file with init values
        # These are tuples defining name init value pair
        self.signallist_write=[
            ('reset', 1),
            ('initdone',0),
            ('io_reference_addr', 0),
            ('io_reference_read_en', 0),
            ('io_reference_write_en', 0),
            ('io_estimate_addr', 0),
            ('io_estimate_read_en', 0),
            ('io_estimate_write_en', 0),
            ('io_estimate_user_index',0),
            ('io_estimate_format',0),
            ('io_reference_in_real',0), 
            ('io_reference_in_imag',0), 
        ]
        for user in range(self.Users):
           self.signallist_write+= [ ('io_estimate_in_%s_real' %(user),0)  , 
                   ('io_estimate_in_%s_imag' %(user) ,0)] 


        #These are signals not in dut
        self.newsigs_read=[
                ]
        self.signallist_read=[
        ]
        for user in range(self.Users):
           self.signallist_read+= [ ('io_estimate_out_%s_real' %(user),0)  , 
                   ('io_estimate_out_%s_imag' %(user) ,0)] 

        self.init()

    def init(self):
        self._vlogparameters =dict([('Rs',self.Rs)])
        # This gets interesting
        # IO is a file data stucture
        iofiles_write=[
                'control_write'
                ]
        for name in iofiles_write:
            self.control_write.Data.Members[name]=verilog_iofile(self,name=name,
                    dir='in',iotype='ctrl')

        self.define_control()
    
    def reset_control_sequence(self):
        f=self.control_write.Data.Members['control_write']
        self.time=0
        f.data= np.array([])
        f.set_control_data(init=0) # Initialize to zeros at time 0


    # First we start to control Verilog simulations with 
    # This controller. I.e we pass the IOfile definition
    def step_time(self,**kwargs):
        self.time+=kwargs.get('step',self.step)

    def define_control(self):
        # This is a bit complex way of passing the data,
        # But eventually we pass only the data , not the file
        # Definition. File should be created in the testbench
        scansigs_write=[]
        for name, val in self.signallist_write:
            # We manipulate connectors as verilog_iofile operate on those
            if name in self.newsigs_write:
                self.connectors.new(name=name, cls='reg')
            else:
                self.connectors.Members[name]=self.dut.io_signals.Members[name] 
                self.connectors.Members[name].init=''
            scansigs_write.append(name) 

        f=self.control_write.Data.Members['control_write']
        f.verilog_connectors=self.connectors.list(names=scansigs_write)
        f.set_control_data(init=0) # Initialize to zeros at time 0

    def reset(self):
        #start defining the file
        f=self.control_write.Data.Members['control_write']
        for name in [ 'reset', ]:
            f.set_control_data(time=self.time,name=name,val=1)

        # After awhile, switch off reset 
        self.step_time(step=15*self.step)

        for name in [ 'reset', ]:
            f.set_control_data(time=self.time,name=name,val=0)

    def reset_estimate_memories(self):
        data=np.zeros((self.symbol_length,self.Users))
        self.write_estimate_sequence(data=data)

    # [TODO]: If signal does not exist, add it to column
    # Enables file initialization without allocation 
    def write_reference_sequence(self,**kwargs):
        f=self.control_write.Data.Members['control_write']
        maxval=kwargs.get('maxval',2**15-1) 
        refseq=(np.array(PLPCsyn_long).reshape(-1,1)*(maxval)).astype(complex)
        #refseq[0]=1 # This is to find sync
        #refseq[-1]=2 # This is to find sync
        #print( refseq )
        f.set_control_data(time=self.time,name='io_reference_write_en',val=1)
        for i in range(self.symbol_length):
            self.step_time()
            f.set_control_data(time=self.time,name='io_reference_addr',val=i)
            f.set_control_data(time=self.time,name='io_reference_in_real',val=refseq[i].real)
            f.set_control_data(time=self.time,name='io_reference_in_imag',val=refseq[i].imag)
            self.step_time()
        f.set_control_data(time=self.time,name='io_reference_addr',val=0)
        f.set_control_data(time=self.time,name='io_reference_write_en',val=0)
        f.set_control_data(time=self.time,name='io_estimate_user_index',val=0)
        self.step_time()

    def write_estimate_sequence(self,**kwargs):
        data=kwargs.get('data') # complex matrix: symbol_length, users
        f=self.control_write.Data.Members['control_write']
        f.set_control_data(time=self.time,name='io_estimate_write_en',val=1)
        step=7*self.step
        for i in range(self.symbol_length):
            self.step_time()
            f.set_control_data(time=self.time,name='io_estimate_addr',val=i)
            for user in range(self.Users):
                f.set_control_data(time=self.time,
                        name='io_estimate_in_%s_real' %(user) ,val=data[i,user].real)
                f.set_control_data(time=self.time,
                        name='io_estimate_in_%s_imag' %(user),val=data[i,user].imag)
            self.step_time()
        f.set_control_data(time=self.time,name='io_estimate_addr',val=0)
        f.set_control_data(time=self.time,name='io_estimate_write_en',val=0)
        self.step_time()

    # This controls only the sync signal of the read
    def read_estimate_out(self,**kwargs):
        f=self.control_write.Data.Members['control_write']
        # Because of the latency from io->mem->output, we must keep the 
        # Read_en high for 7 clock cycles 
        step=7*self.step
        for i in range(self.symbol_length):
            self.step_time(step=step)
            f.set_control_data(time=self.time,name='io_estimate_addr',val=i)
            f.set_control_data(time=self.time,name='io_estimate_read_en',val=1)
            self.step_time(step=step)
            f.set_control_data(time=self.time,name='io_estimate_read_en',val=0)

    def start_datafeed(self):
        f=self.control_write.Data.Members['control_write']
        for name in [ 'initdone', ]:
            f.set_control_data(time=self.time,name=name,val=1)
        self.step_time()

    def set_estimate_format(self,**kwargs):
        f=self.control_write.Data.Members['control_write']
        value=kwargs.get('value',0)
        f.set_control_data(time=self.time,name='io_estimate_format',val=value)

    def set_estimate_zeros(self,**kwargs):
        f=self.control_write.Data.Members['control_write']
        addresses=kwargs.get('addresses',[0,1,2,3,4,5,32,59,60,61,62,63])
        f.set_control_data(time=self.time,name='io_estimate_write_en',val=1)
        for addr in addresses:
            f.set_control_data(time=self.time,name='io_estimate_addr',val=addr)
            for i in range(self.Users):
                f.set_control_data(time=self.time,name='io_estimate_in_%s_real' %(i),val=0)
                f.set_control_data(time=self.time,name='io_estimate_in_%s_imag' %(i),val=0)
                self.step_time()
        f.set_control_data(time=self.time,name='io_estimate_write_en',val=0)








