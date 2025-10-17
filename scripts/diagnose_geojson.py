
import geopandas as gpd
import os

# --- 設定 ---
# このスクリプトから見た、GeoJSONファイルへの相対パス
GEOJSON_FILE_PATH = '../data/nz_population.geojson'
# ---

def diagnose_geojson(file_path):
    """
    GeoJSONファイルを読み込み、無効または空のジオメトリがないかチェックします。
    """
    print(f"--- 診断開始: {file_path} ---")

    # ファイルの存在確認
    if not os.path.exists(file_path):
        print(f"エラー: ファイルが見つかりません '{file_path}'")
        print("GEOJSON_FILE_PATHが正しいか確認してください。")
        return

    # ファイル読み込み
    try:
        gdf = gpd.read_file(file_path)
        print(f"ファイル読み込み成功。{len(gdf)}個の地物が見つかりました。")
    except Exception as e:
        print(f"ファイル読み込みエラー: {e}")
        print("ファイルが破損しているか、有効なGeoJSON形式ではない可能性があります。")
        return

    # --- ジオメトリ（形状）のチェック ---
    print("\n--- ジオメトリのチェック中 ---")

    # 1. 空のジオメトリがないかチェック
    empty_geometries = gdf[gdf.geometry.is_empty]
    if not empty_geometries.empty:
        print(f"警告: {len(empty_geometries)}個の空のジオメトリが見つかりました。")
    else:
        print("空のジオメトリはありませんでした。")

    # 2. 無効なジオメトリがないかチェック
    invalid_geometries = gdf[~gdf.geometry.is_valid]
    if not invalid_geometries.empty:
        print(f"★問題発見★: {len(invalid_geometries)}個の無効なジオメトリが見つかりました。")
        print("これが地図の描画に失敗する、ほぼ確実な原因です。")
    else:
        print("すべてのジオメトリは有効です。")

    print("\n--- 診断完了 ---")
    if not invalid_geometries.empty:
        print("結論: 無効なジオメトリが発見されました。これがコロプレス地図が表示されない原因である可能性が非常に高いです。")
        print("提案: QGISなどのGISツールでファイルを開き、「ジオメトリの修正」アルゴリズムを実行してください。")
    elif not empty_geometries.empty:
        print("結論: 空のジオメトリが見つかりました。これも問題の原因である可能性があります。")
    else:
        print("結論: この基本的なチェックでは、明らかなジオメトリエラーは見つかりませんでした。問題はより複雑（例: 形状が複雑すぎるなど）である可能性があります。")


if __name__ == '__main__':
    diagnose_geojson(GEOJSON_FILE_PATH)
