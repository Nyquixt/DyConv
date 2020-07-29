import torch
import torch.nn as nn

__all__ = ['CondConv']

class CondConv(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride=1, padding=0, groups=1, bias=False):
        super(CondConv, self).__init__()

        self.avg_pool = nn.AdaptiveAvgPool2d(1)

        self.one_conv = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, groups=groups, bias=bias)
        self.two_conv = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, groups=groups, bias=bias)
        self.three_conv = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, groups=groups, bias=bias)
        self.attention = nn.Sequential(
            nn.Linear(in_channels, 3),
            nn.Sigmoid()
        )

    def forward(self, x):
        one_out = self.one_conv(x).unsqueeze(dim=1)
        two_out = self.two_conv(x).unsqueeze(dim=1)
        three_out = self.three_conv(x).unsqueeze(dim=1)
        all_out = torch.cat([one_out, two_out, three_out], dim=1)
        gap = self.avg_pool(x).squeeze(dim=-1).squeeze(dim=-1)
        weights = self.attention(gap).unsqueeze(dim=-1).unsqueeze(dim=-1).unsqueeze(dim=-1)
        out = weights * all_out
        out = out.sum(dim=1, keepdim=False)
        return out

def test():
    x = torch.randn(4, 3 , 32, 32)
    conv = CondConv(x.size(1), 64, 3)
    y = conv(x)
    print(y.size())

# test()