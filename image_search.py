from bing_image_downloader import downloader
import configparser


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('config.ini',encoding='utf-8')
    query_string = config['image_search']['query_string']
    limit = int(config['image_search']['limit'])
    output_dir = config['image_search']['output_dir']
    downloader.download(
        query_string, 
        limit=limit,  
        output_dir=output_dir, 
    )