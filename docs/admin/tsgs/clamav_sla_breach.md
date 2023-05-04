# ClamAV SLA Breach
ClamAV is currently the approved antivirus solution of 1P Linux workloads (SBI and Mariner). For historical reasons, the signatures are [hosted on PMC](https://packages.microsoft.com/clamav/).

We currently have no established SLA with regards to these signatures, and are urging the Azure Security Monitoring (ASM) team (who owns this scenario) to host/manage these signatures themselves.

If an IcM is raised regarding a breach of SLA for ClamAV signatures, kindly close the incident, indicating that no SLA is defined or agreed upon. For questions, defer to mbearup.

The Azure Security Monitoring (ASM) team is deprecating ClamAV in favor of Microsoft Defender (MDE) in 2024. So this should "go away" over time.