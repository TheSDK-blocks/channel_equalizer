add wave -position insertpoint  \
sim:/tb_channel_equalizer/reset \
sim:/tb_channel_equalizer/clock \
sim:/tb_channel_equalizer/io_reference_in_real \
sim:/tb_channel_equalizer/io_reference_in_imag \
sim:/tb_channel_equalizer/io_reference_addr \
sim:/tb_channel_equalizer/io_reference_write_en \
sim:/tb_channel_equalizer/channel_equalizer/memblock/mem_real \
sim:/tb_channel_equalizer/channel_equalizer/memblock/io_write_addr \
sim:/tb_channel_equalizer/channel_equalizer/memblock/io_write_val_real \
sim:/tb_channel_equalizer/channel_equalizer/memblock/io_write_val_imag \
sim:/tb_channel_equalizer/channel_equalizer/memblock/mem_imag \
sim:/tb_channel_equalizer/channel_equalizer/edge_detector_io_rising \
sim:/tb_channel_equalizer/channel_equalizer/edge_detector_1_io_rising \
sim:/tb_channel_equalizer/channel_equalizer/edge_detector_2_io_rising \
sim:/tb_channel_equalizer/channel_equalizer/edge_detector_3_io_rising \
sim:/tb_channel_equalizer/channel_equalizer/edge_detector_4_io_rising \
sim:/tb_channel_equalizer/channel_equalizer/edge_detector_5_io_rising \

run -all 
//sim:/tb_f2_dsp/f2_dsp/f2_rx_dsp/f2_rx_path/w_weighted_users_0_real \ \
//sim:/tb_f2_dsp/f2_dsp/f2_rx_dsp/f2_rx_path/w_weighted_users_0_imag \ \
//sim:/tb_f2_dsp/f2_dsp/f2_rx_dsp/f2_rx_path/io_adc_ioctrl_user_weights_0_real \ \
//sim:/tb_f2_dsp/f2_dsp/f2_rx_dsp/f2_rx_path/io_adc_ioctrl_user_weights_0_imag \ \
 \
