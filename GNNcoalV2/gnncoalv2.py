# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/gnncoalv2.ipynb.

# %% auto 0
__all__ = ['seed_everything', 'GNN', 'DiffPoolConvolutionPart', 'MiniDenseNet', 'mean_over_n', 'GNNcoalV2']

# %% ../nbs/gnncoalv2.ipynb 2
import torch
import torch.nn as nn
from torch_geometric.nn.dense.dense_gcn_conv import DenseGCNConv
from math import ceil
import torch.nn.functional as F
from torch_geometric.nn import dense_diff_pool
from x_transformers import Encoder

import random
import numpy as np
import torch

# %% ../nbs/gnncoalv2.ipynb 3
def seed_everything(seed=42):
    """Seed all random number generators."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    
    # Ensure deterministic behavior (this can slow down training, so you might not always want it)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

# Example usage:
# seed_everything(42)


# %% ../nbs/gnncoalv2.ipynb 5
class GNN(nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, linearize=True):
        super(GNN, self).__init__()

        self.convs = nn.ModuleList([
            DenseGCNConv(in_channels, hidden_channels, improved=True),
            DenseGCNConv(hidden_channels, hidden_channels, improved=True),
            DenseGCNConv(hidden_channels, out_channels, improved=True)
        ])

        self.norms = nn.ModuleList([
            nn.LayerNorm(hidden_channels),
            nn.LayerNorm(hidden_channels),
            nn.LayerNorm(out_channels)
        ])

        self.linearize = linearize
        if self.linearize: self.linear = nn.Linear(2 * hidden_channels + out_channels, out_channels)
        else: self.linear = None
        

    def forward(self, x, adj):
        xs = []
        for conv, norm in zip(self.convs, self.norms):
            x = F.relu(conv(x, adj))
            x = norm(x)
            xs.append(x)
        x = torch.cat(xs, dim=-1)
        
        if self.linearize: return F.relu(self.linear(x))
        else: return x

# %% ../nbs/gnncoalv2.ipynb 7
class DiffPoolConvolutionPart(nn.Module):
    def __init__(self, max_nodes, num_features, num_hidden=64):
        super().__init__()

        self.layers = nn.ModuleList([])
        num_nodes = ceil(0.3 * max_nodes)
        
        for _ in range(3):
            layer = nn.ModuleDict({
                'pool': GNN(num_features, num_hidden, num_nodes),
                'embed': GNN(num_features, num_hidden, num_hidden, linearize=False)
            })
            self.layers.append(layer)
            
            num_features = 3 * num_hidden
            num_nodes = ceil(0.3 * num_nodes)
            
        self.gnn3_embed = GNN(3 * num_hidden, num_hidden, num_hidden, linearize=False)

    def forward(self, x, adj, batch_size, num_trees=500):
        l_total, e_total = 0, 0
        for layer in self.layers:
            s = layer['pool'](x, adj)
            x = layer['embed'](x, adj)
            x, adj, l, e = dense_diff_pool(x, adj, s)
            l_total += l
            e_total += e
            
        x = self.gnn3_embed(x, adj)
        x = x.mean(dim=1)
        x = x.view(batch_size, num_trees, x.shape[-1])
        
        return x, l_total, e_total
        
#model = GNNcoalV2(max_nodes=19, num_features=60, num_hidden=64,  out_channels=60)

# %% ../nbs/gnncoalv2.ipynb 8
class MiniDenseNet(nn.Module):
    def __init__(self, in_features, hidden_features, out_features):
        super(MiniDenseNet, self).__init__()

        self.net = nn.Sequential(
            nn.Linear(in_features, hidden_features),
            nn.ReLU(),
            nn.Linear(hidden_features, hidden_features),
            nn.ReLU(),
            nn.Linear(hidden_features, out_features),
        )

    def forward(self, x):
        return self.net(x)

# %% ../nbs/gnncoalv2.ipynb 9
def mean_over_n(emb, n=10):
    # Unfold the tensor along dimension 1, using size n and step n
    unfolded = emb.unfold(1, n, n)
    # Compute the mean over the new last dimension
    mean_values = unfolded.mean(dim=-1)
    return mean_values

# %% ../nbs/gnncoalv2.ipynb 10
class GNNcoalV2(nn.Module):
    def __init__(self, max_nodes, num_features, num_hidden=64, out_dim=60,
                 enc_heads = 4, enc_depth=8, num_trees=1000
                ):
        super().__init__()

        self.conv = DiffPoolConvolutionPart(max_nodes=max_nodes,
                                            num_features=num_features,
                                            num_hidden=num_hidden)
        enc_dim = num_hidden * 3
        self.encoder = Encoder(dim=enc_dim, depth=enc_depth, heads=enc_heads,
                               ff_glu=True, residual_attn=True, flash=True)

        self.positional_encodings = nn.Parameter(torch.randn(num_trees, enc_dim))
        self.demography_head = MiniDenseNet(enc_dim, enc_dim//2, out_dim)
        

    def forward(self, x, adj, batch_size, num_trees=500):
        emb, l_total, e_total = self.conv(x, adj, batch_size, num_trees)
        emb = emb + self.positional_encodings.unsqueeze(0)
        emb = self.encoder(emb)    
        
        #emb = emb.sum(dim=1)
        #alpha_emb = mean_over_n(emb, num_trees_for_alpha)

        emb = self.demography_head(emb)
        return emb, l_total, e_total
        

# model = GNNcoalV2(max_nodes=19, num_features=60, num_hidden=64,  out_dim=60,
#                   enc_heads=4, enc_depth=8,
#                  )
