import hre from "hardhat";

async function main() {
  const EvidenceRegistry = await hre.ethers.getContractFactory("EvidenceRegistry");
  const evidenceRegistry = await EvidenceRegistry.deploy();

  await evidenceRegistry.waitForDeployment();
  const address = await evidenceRegistry.getAddress();

  console.log("EvidenceRegistry deployed to:", address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
