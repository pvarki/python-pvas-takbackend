from pttbackend.security import PipelineTokens

print("** basic auth")
print(PipelineTokens.singleton().bearer)
print("** ssh key")
print(PipelineTokens.singleton().ssh_pub)
