import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Timeattack Code Dojo",
    short_name: "Code Dojo",
    description: "제한 시간 안에 집중하고, 제출하고, 성장하는 실전 코딩 훈련장",
    start_url: "/",
    display: "standalone",
    background_color: "#07091b",
    theme_color: "#07091b",
    orientation: "any",
    categories: ["education", "productivity", "developer"],
    icons: [
      {
        src: "/timeattack-code-dojo-icon.png",
        sizes: "1618x1618",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/timeattack-code-dojo-icon.png",
        sizes: "1618x1618",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
