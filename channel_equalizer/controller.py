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
        self.Users = 16;                   # Number of users
        self.symbol_length  = 64;          # OFDM symbol length
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
        self.newsigs=[
                 'initdone',
                ]

        # Selected signals controlled with this file with init values
        # These are tuples defining name init value pair
        self.signallist=[
            ('reset', 1),
            ('initdone',0),
            ('io_reference_addr', 0),
            ('io_reference_write_en', 0),
            ('io_estimate_addr', 0),
            ('io_estimate_write_en', 0),
            ('io_estimate_user_index',0),
            ('io_estimate_sync',0),
            ('io_reference_in_real',0), 
            ('io_reference_in_imag',0),
        ]

        self.init()

    def init(self):
        self._vlogparameters =dict([('Rs',self.Rs)])
        # This gets interesting
        # IO is a file data stucture
        scanfiles=[
                'control_file'
                ]
        for name in scanfiles:
            self.control_write.Data.Members[name]=verilog_iofile(self,name=name,
                    dir='in',iotype='ctrl')
        #f=self.control_write.Data.Members['control_file']
        self.define_control()
        self.reset()
        
    # First we start to control Verilog simulations with 
    # This controller. I.e we pass the IOfile definition

    def define_control(self):
        # This is a bit complex way of passing the data,
        # But eventually we pass only the data , not the file
        # Definition. File should be created in the testbench
        scansigs=[]
        for name, val in self.signallist:
            # We manipulate connectors as verilog_iofile operate on those
            if name in self.newsigs:
                self.connectors.new(name=name, cls='reg')
            else:
                self.connectors.Members[name]=self.dut.io_signals.Members[name] 
                self.connectors.Members[name].init=''
            scansigs.append(name) 

        f=self.control_write.Data.Members['control_file']
        f.verilog_connectors=self.connectors.list(names=scansigs)
        f.set_control_data(init=0) # Initialize to zeros at time 0
        for name, val in self.signallist:
            f.set_control_data(time=0,name=name,val=val) 

    def reset(self):
        #start defining the file
        f=self.control_write.Data.Members['control_file']
        step=int(1/(self.Rs*1e-12))

        time=0
        for name in [ 'reset', ]:
            f.set_control_data(time=time,name=name,val=1)

        # After awhile, switch off reset 
        time=int(16/(self.Rs*1e-12))

        for name in [ 'reset', ]:
            f.set_control_data(time=time,name=name,val=0)
        time+=step

        refseq=(np.array(PLPCsyn_long).reshape(-1,1)*(2**15-1)).astype(complex)
        refseq[0]=1 # This is to find sync
        refseq[-1]=2 # This is to find sync
        print( refseq )
        f.set_control_data(time=time,name='io_reference_write_en',val=1)
        sequence=range(64)
        addr=0
        for i in range(64):
            time+=step
            f.set_control_data(time=time,name='io_reference_addr',val=i)
            f.set_control_data(time=time,name='io_reference_in_real',val=refseq[i].real)
            f.set_control_data(time=time,name='io_reference_in_imag',val=refseq[i].imag)
        time+=step
        f.set_control_data(time=time,name='io_reference_addr',val=0)
        f.set_control_data(time=time,name='io_reference_write_en',val=0)
        f.set_control_data(time=time,name='io_estimate_user_index',val=0)
        time+=step
        for name in [ 'initdone', ]:
            f.set_control_data(time=time,name=name,val=1)
        time+=step
        f.set_control_data(time=time,name='io_estimate_sync',val=1)
        time+=step
        time+=step
        f.set_control_data(time=time,name='io_estimate_sync',val=0)
        self.curr_time=time

