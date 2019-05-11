add wave -position insertpoint  \
sim:/tb_channel_equalizer/reset \
sim:/tb_channel_equalizer/clock \
sim:/tb_channel_equalizer/io_reference_in_real \
sim:/tb_channel_equalizer/io_reference_in_imag \
sim:/tb_channel_equalizer/io_reference_addr \
sim:/tb_channel_equalizer/io_reference_write_en \
sim:/tb_channel_equalizer/channel_equalizer/memblock/mem_real \
sim:/tb_channel_equalizer/channel_equalizer/memblock/mem_imag \
sim:/tb_channel_equalizer/channel_equalizer/memblock/io_write_addr \
sim:/tb_channel_equalizer/channel_equalizer/memblock/io_write_val_real \
sim:/tb_channel_equalizer/channel_equalizer/memblock/io_write_val_imag \
sim:/tb_channel_equalizer/channel_equalizer/memblock_1/mem_real \
sim:/tb_channel_equalizer/channel_equalizer/memblock_1/mem_imag \
sim:/tb_channel_equalizer/channel_equalizer/memblock_1/io_write_en \
sim:/tb_channel_equalizer/channel_equalizer/memblock_1/io_write_addr \
sim:/tb_channel_equalizer/channel_equalizer/io_estimate_sync \
sim:/tb_channel_equalizer/channel_equalizer/io_estimate_user_index \
sim:/tb_channel_equalizer/channel_equalizer/equalize_address_counter \
sim:/tb_channel_equalizer/channel_equalizer/estimate_address_counter \
sim:/tb_channel_equalizer/channel_equalizer/complex_reciprocal/io_N_real \
sim:/tb_channel_equalizer/channel_equalizer/complex_reciprocal/io_N_imag \
sim:/tb_channel_equalizer/channel_equalizer/complex_reciprocal/io_D_real \
sim:/tb_channel_equalizer/channel_equalizer/complex_reciprocal/io_D_imag \
sim:/tb_channel_equalizer/channel_equalizer/r_A_real \
sim:/tb_channel_equalizer/channel_equalizer/r_A_imag \
sim:/tb_channel_equalizer/channel_equalizer/r_estimate_sync \
sim:/tb_channel_equalizer/channel_equalizer/r_equalize_sync \
sim:/tb_channel_equalizer/channel_equalizer/edge_detector_5/io_rising \
sim:/tb_channel_equalizer/channel_equalizer/complex_reciprocal/io_Q_real \
sim:/tb_channel_equalizer/channel_equalizer/complex_reciprocal/io_Q_imag \

run -all

