# Copyright (c) Meta Platforms, Inc. and affiliates.
# This software may be used and distributed according to the terms of the Llama 2 Community License Agreement.

import fire
import os
import torch

from llama import Llama

USE_CUDA = os.environ.get('USE_CUDA', False)

# Some how xla init will slow down the CUDA speed.
if USE_CUDA:
    import torch.multiprocessing as xmp
else:
    import torch_xla.debug.profiler as xp
    import torch_xla.distributed.xla_multiprocessing as xmp

def main(
    ckpt_dir: str,
    tokenizer_path: str,
    temperature: float = 0.6,
    top_p: float = 0.9,
    max_seq_len: int = 128,
    max_gen_len: int = 64,
    max_batch_size: int = 4,
    dynamo: bool = True,
    spmd: bool = True,
    enable_activation_sharding: bool = False,
    enable_kv_cache_sharding: bool = True,
):
    if not USE_CUDA:
        # server = xp.start_server(9012, only_on_master=False)
        pass
    generator = Llama.build(
        ckpt_dir=ckpt_dir,
        tokenizer_path=tokenizer_path,
        max_seq_len=max_seq_len,
        max_batch_size=max_batch_size,
        dynamo=dynamo,
        spmd=spmd,
        enable_activation_sharding=enable_activation_sharding,
        enable_kv_cache_sharding=enable_kv_cache_sharding,
    )

    print(f'[WONJOO] max_batch_size={max_batch_size}')

    prompts = [
        # For these prompts, the expected answer is the natural continuation of the prompt
        "I believe the meaning of life is",
        "Simply put, the theory of relativity states that ",
        """A brief message congratulating the team on the launch:

        Hi everyone,
        
        I just """,
        # Few shot prompt (providing a few examples before asking model to complete more);
        """Translate English to French:
        
        sea otter => loutre de mer
        peppermint => menthe poivrée
        plush girafe => girafe peluche
        cheese =>""",
    ]

    import time
    # print("About to start in 10 seconds")
    #server = xp.start_server(9012, only_on_master=False)
    time.sleep(2)
    print("Starting!")

    for i in range(2):
        with torch.no_grad():
            if i == 1:
                profile_logdir = os.environ['PROFILE_LOGDIR']
                # Use trace_detached to capture the profile from a background thread
                #xp.trace_detached('localhost:9012', profile_logdir, duration_ms=10000)

            results = generator.text_completion(
                prompts,
                max_gen_len=max_gen_len,
                temperature=temperature,
                top_p=top_p,
            )
            for prompt, result in zip(prompts, results):
                print(prompt)
                print(f"> {result['generation']}")
                print("\n==================================\n")

    print("Finished!")


def _fn(
    idx,
    ckpt_dir: str,
    tokenizer_path: str,
    temperature: float = 0.6,
    top_p: float = 0.9,
    max_seq_len: int = 128,
    max_gen_len: int = 64,
    max_batch_size: int = 4,
    dynamo: bool = True,
    spmd: bool = True,
    enable_activation_sharding: bool = False,
    enable_kv_cache_sharding: bool = True,
):
    if USE_CUDA:
        os.environ['WORLD_SIZE'] = torch.cuda.device_count()
        os.environ['RANK'] = idx
        os.environ['LOCAL_RANK'] = idx
    main(ckpt_dir, tokenizer_path, temperature, top_p, max_seq_len, max_gen_len, max_batch_size, dynamo, spmd, enable_activation_sharding, enable_kv_cache_sharding)


def mp_main(
    mp: bool,
    ckpt_dir: str,
    tokenizer_path: str,
    temperature: float = 0.6,
    top_p: float = 0.9,
    max_seq_len: int = 128,
    max_gen_len: int = 64,
    max_batch_size: int = 4,
    dynamo: bool = True,
    spmd: bool = True,
    enable_activation_sharding: bool = False,
    enable_kv_cache_sharding: bool = True,
):
    if mp:
        if USE_CUDA:
            kwargs = {"nprocs": torch.cuda.device_count(),
                      "join": True}
        else:
            kwargs = {}
        xmp.spawn(_fn,
                  args=(ckpt_dir, tokenizer_path, temperature, top_p, max_seq_len, max_gen_len, max_batch_size, dynamo, spmd, enable_activation_sharding, enable_kv_cache_sharding), **kwargs)
    else:
        main(ckpt_dir, tokenizer_path, temperature, top_p, max_seq_len, max_gen_len, max_batch_size, dynamo, spmd, enable_activation_sharding, enable_kv_cache_sharding)


if __name__ == "__main__":
    fire.Fire(mp_main)
