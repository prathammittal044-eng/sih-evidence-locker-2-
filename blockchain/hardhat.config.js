import "@nomicfoundation/hardhat-toolbox";
export default {
  solidity: "0.8.20",
  networks: {
    amoy: {
      url: "https://rpc-amoy.polygon.technology",
      accounts: ["3ed05d7d9f6885150c28e92adefd6f556d4769b84990a8cf0c26df143e2e27ce"]
    }
  }
};
